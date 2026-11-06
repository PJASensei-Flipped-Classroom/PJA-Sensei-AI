import hashlib
import ipaddress
import logging
import math
import re
import socket
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.domain.exceptions import SsrfBlockedError
from app.domain.ports import RagChunk, RagPort
from app.domain.sensei import ReferenceMaterial

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.errors import ChromaError

    HAS_CHROMADB = True
except ImportError:
    chromadb = None  # type: ignore[assignment]
    ChromaError = OSError  # type: ignore[misc,assignment]
    HAS_CHROMADB = False

# Operational failures from optional Chroma / embedding paths (no stable narrow hierarchy when missing).
_CHROMA_OP_ERRORS = (ChromaError, OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError)

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "169.254.169.254",
}

def _is_ip_forbidden(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False
def validate_safe_url(url: str) -> str:
    if not url or not url.strip():
        raise SsrfBlockedError(url, "Empty URL")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise SsrfBlockedError(
            url, f"Forbidden URL scheme '{parsed.scheme}' (only http/https allowed)"
        )

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise SsrfBlockedError(url, "Missing hostname in URL")

    if (
        hostname in FORBIDDEN_HOSTNAMES
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or hostname.endswith(".localhost")
    ):
        raise SsrfBlockedError(url, f"Forbidden local/internal host: {hostname}")

    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or 80)
    except socket.gaierror as exc:
        raise SsrfBlockedError(
            url, f"Cannot resolve hostname '{hostname}' (DNS lookup failed)"
        ) from exc

    if not addr_info:
        raise SsrfBlockedError(url, f"No DNS records found for hostname '{hostname}'")

    for entry in addr_info:
        resolved_ip = entry[4][0]
        if _is_ip_forbidden(resolved_ip):
            raise SsrfBlockedError(
                url, f"Host '{hostname}' resolves to a forbidden IP address: {resolved_ip}"
            )
    return url.strip()

def _strip_html(raw_html: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html or "", "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
    except (ImportError, TypeError, ValueError, AttributeError):
        text = re.sub(
            r"<(script|style).*?>.*?</\1>",
            " ",
            raw_html or "",
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()


def _extract_pdf_text(raw_bytes: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(raw_bytes))
    parts: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            parts.append(page_text.strip())
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _decode_fetched_content(url: str, raw_bytes: bytes, content_type: str = "") -> str:
    ct = (content_type or "").lower()
    looks_pdf = "application/pdf" in ct or url.lower().split("?", 1)[0].endswith(".pdf")
    if looks_pdf:
        try:
            from pypdf.errors import PdfReadError
        except ImportError:  # pragma: no cover
            PdfReadError = ValueError  # type: ignore[misc,assignment]
        try:
            pdf_text = _extract_pdf_text(raw_bytes)
            if pdf_text:
                return pdf_text
        except (ImportError, PdfReadError, ValueError, TypeError, OSError, KeyError):
            logger.warning("PDF text extraction failed for url=%s", url, exc_info=True)
    text = raw_bytes.decode("utf-8", errors="replace")
    if "html" in ct or "<html" in text[:500].lower() or "<body" in text[:500].lower():
        return _strip_html(text)
    return re.sub(r"\s+", " ", text).strip()

def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks = []
    start = 0
    while start < len(cleaned):
        end = start + chunk_size
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start = max(start + 1, end - overlap)
    return chunks
def _embed_text(text: str, dim: int = 64) -> List[float]:
    vec = [0.0] * dim
    tokens = re.findall(r"\w+", (text or "").lower())
    if not tokens:
        vec[0] = 1.0
        return vec
    for token in tokens:
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
def _cosine_similarity(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
class ChromaRagAdapter(RagPort):
    def __init__(self, fetcher: Optional[Callable[[str], str]] = None):
        self.fetcher = fetcher
        self._chroma_client = None
        self._collections: Dict[str, Any] = {}
        self._fallback_store: Dict[str, List[Tuple[List[float], RagChunk]]] = {}
        self._healthy = False

        if HAS_CHROMADB and chromadb is not None:
            try:
                self._chroma_client = chromadb.EphemeralClient()
                self._healthy = True
            except _CHROMA_OP_ERRORS:
                logger.exception("Chroma init failed; using in-process fallback store")
                self._chroma_client = None
                self._healthy = True
        else:
            logger.warning("chromadb not installed; using hash-embedding fallback store")
            self._healthy = True

    def is_healthy(self) -> bool:
        if self._chroma_client is not None:
            try:
                self._chroma_client.heartbeat()
                return True
            except _CHROMA_OP_ERRORS:
                return False
        return self._healthy
    def _fetch_material_text(self, material: ReferenceMaterial):
        if material.content and material.content.strip():
            return f"{material.title}. {material.content.strip()}"

        safe_url = validate_safe_url(material.link)

        if self.fetcher is not None:
            raw = self.fetcher(safe_url)
            if isinstance(raw, (bytes, bytearray)):
                body = _decode_fetched_content(safe_url, bytes(raw))
            else:
                body = _strip_html(str(raw))
            return f"{material.title}. {body}"

        try:
            with httpx.Client(timeout=settings.RAG_FETCH_TIMEOUT, follow_redirects=False) as client:
                resp = client.get(safe_url)
                if resp.status_code == 200 and resp.content:
                    max_bytes = int(settings.RAG_FETCH_MAX_BYTES)
                    raw = resp.content[:max_bytes] if max_bytes > 0 else resp.content
                    if 0 < max_bytes < len(resp.content):
                        logger.warning(
                            "RAG fetch truncated url=%s from %s to %s bytes",
                            safe_url,
                            len(resp.content),
                            max_bytes,
                        )
                    body = _decode_fetched_content(
                        safe_url,
                        raw,
                        content_type=resp.headers.get("content-type", ""),
                    )
                    if body:
                        return f"{material.title}. {body}"
        except (httpx.HTTPError, OSError, ValueError, TypeError):
            logger.warning("RAG fetch failed url=%s", safe_url, exc_info=True)

        return f"{material.title} ({safe_url})"
    def ingest(self, conversation_id: str, materials: List[ReferenceMaterial]) -> int:
        if not materials:
            return 0

        chunks_to_store: List[RagChunk] = []
        for mat in materials:
            full_text = self._fetch_material_text(mat)
            for piece in _chunk_text(full_text):
                chunks_to_store.append(
                    RagChunk(title=mat.title, link=mat.link, snippet=piece)
                )
        if not chunks_to_store:
            return 0

        if self._chroma_client is not None:
            try:
                col_name = f"conv_{conversation_id.replace('-', '_')}"[:60]
                collection = self._chroma_client.get_or_create_collection(name=col_name)
                ids = [f"{conversation_id}_{i}" for i in range(len(chunks_to_store))]
                embeddings = [_embed_text(c.snippet) for c in chunks_to_store]
                documents = [c.snippet for c in chunks_to_store]
                metadatas = [{"title": c.title, "link": c.link} for c in chunks_to_store]
                collection.upsert(
                    ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
                )
                self._collections[conversation_id] = col_name
            except _CHROMA_OP_ERRORS:
                logger.warning(
                    "Chroma ingest failed conversation_id=%s; using fallback store",
                    conversation_id,
                    exc_info=True,
                )

        self._fallback_store[conversation_id] = [
            (_embed_text(c.snippet), c) for c in chunks_to_store
        ]
        return len(chunks_to_store)
    def retrieve(self, conversation_id: str, query: str, top_k: int = 3) -> List[RagChunk]:
        if not query or not query.strip():
            return []

        query_vec = _embed_text(query)

        if self._chroma_client is not None and conversation_id in self._collections:
            try:
                col_name = self._collections[conversation_id]
                collection = self._chroma_client.get_collection(name=col_name)
                res = collection.query(query_embeddings=[query_vec], n_results=top_k)
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                results: List[RagChunk] = []
                for doc, meta in zip(docs, metas):
                    if doc and isinstance(meta, dict):
                        results.append(
                            RagChunk(
                                title=str(meta.get("title", "Źródło")),
                                link=str(meta.get("link", "")),
                                snippet=str(doc)
                            )
                        )
                if results:
                    return results
            except _CHROMA_OP_ERRORS:
                logger.warning(
                    "Chroma retrieve failed conversation_id=%s; using fallback store",
                    conversation_id,
                    exc_info=True,
                )
        entries = self._fallback_store.get(conversation_id, [])
        if not entries:
            return []

        scored = sorted(
            entries,
            key=lambda item: _cosine_similarity(query_vec, item[0]),
            reverse=True,
        )
        return [chunk for _, chunk in scored[:top_k]]

    def delete_conversation(self, conversation_id: str) -> None:
        self._fallback_store.pop(conversation_id, None)
        col_name = self._collections.pop(conversation_id, None)
        if self._chroma_client is not None and col_name:
            try:
                self._chroma_client.delete_collection(name=col_name)
            except _CHROMA_OP_ERRORS:
                logger.warning(
                    "Chroma delete_collection failed conversation_id=%s col=%s",
                    conversation_id,
                    col_name,
                    exc_info=True,
                )