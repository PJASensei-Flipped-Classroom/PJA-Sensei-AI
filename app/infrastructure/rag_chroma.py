import hashlib
import ipaddress
import math
import re
import socket
from typing import List, Dict, Optional, Callable, Any, Tuple
from urllib.parse import urlparse

import httpx

from app.domain.ports import RagPort, RagChunk
from app.domain.sensei import ReferenceMaterial
from app.domain.exceptions import SsrfBlockedError
from app.core.config import settings

try:
    import chromadb
    HAS_CHROMADB = True
except Exception:
    HAS_CHROMADB = False

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
        raise SsrfBlockedError(url, "Pusty adres URL")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise SsrfBlockedError(url, f"Niedozwolony schemat URL '{parsed.scheme}' (dozwolone tylko http/https)")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise SsrfBlockedError(url, "Brak nazwy hosta w adresie URL")

    if (
        hostname in FORBIDDEN_HOSTNAMES
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or hostname.endswith(".localhost")
    ):
        raise SsrfBlockedError(url, f"Niedozwolony host lokalny/wewnętrzny: {hostname}")

    try:
        addr_info = socket.getaddrinfo(hostname, parsed.port or 80)
        for entry in addr_info:
            resolved_ip = entry[4][0]
            if _is_ip_forbidden(resolved_ip):
                raise SsrfBlockedError(
                    url, f"Domena '{hostname}' wskazuje na niedozwolony adres IP: {resolved_ip}"
                )
    except socket.gaierror:
        pass
    return url.strip()

def _strip_html(raw_html: str) -> str:
    text = re.sub(r"<(script|style).*?>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
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
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
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

        if HAS_CHROMADB:
            try:
                self._chroma_client = chromadb.EphemeralClient()
                self._healthy = True
            except Exception:
                self._chroma_client = None
                self._healthy = True
        else:
            self._healthy = True

    def is_healthy(self) -> bool:
        if self._chroma_client is not None:
            try:
                self._chroma_client.heartbeat()
                return True
            except Exception:
                return False
        return self._healthy
    def _fetch_material_text(self, material: ReferenceMaterial):
        safe_url = validate_safe_url(material.link)

        if material.content and material.content.strip():
            return f"{material.title}. {material.content.strip()}"

        if self.fetcher is not None:
            raw = self.fetcher(safe_url)
            return f"{material.title}. {_strip_html(raw)}"

        try:
            with httpx.Client(timeout=settings.RAG_FETCH_TIMEOUT, follow_redirects=False) as client:
                resp = client.get(safe_url)
                if resp.status_code == 200 and resp.text:
                    return f"{material.title}. {_strip_html(resp.text)}"
        except Exception:
            pass

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
            except Exception:
                pass

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
            except Exception:
                pass
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
            except Exception:
                pass