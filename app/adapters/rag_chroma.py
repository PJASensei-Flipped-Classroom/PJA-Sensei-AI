"""Adapter RAG: integracja bazy wektorowej ChromaDB z pobieraniem materiałów HTML i PDF."""

from __future__ import annotations

import io
import ipaddress
import logging
import re
from typing import Any
import uuid
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import chromadb
from chromadb.utils import embedding_functions
import httpx

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 60
RETRIEVE_TOP_K = 3

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
    }
)


def is_safe_rag_url(url: str) -> bool:
    """Odrzuca non-http(s), localhost i prywatne/link-local adresy (ochrona przed SSRF)."""
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host or host in _BLOCKED_HOSTS or host.endswith(".localhost"):
        return False

    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return True  # nazwa DNS — pozwalamy (lab); blokujemy tylko literały IP prywatne

    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


class RagService:
    """Indeksuje materiały sesyjne w ChromaDB i wyszukuje fragmenty do promptu LLM."""

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        chroma_client: chromadb.ClientAPI | None = None,
    ) -> None:
        self.chroma_client = chroma_client or chromadb.Client()
        self._http_client = http_client
        self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        # Przechowuje źródła niemające treści tekstowej (np. znaczniki wideo)
        self._citation_only: dict[str, list[dict[str, Any]]] = {}

    @staticmethod
    def _sanitize_collection_name(conversation_id: str) -> str:
        """Zwraca nazwę kolekcji zgodną z wymogami ChromaDB (alfanumeryczna, max 63 znaki)."""
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", conversation_id)
        return f"pja_kb_{safe_id}"[:63]

    def delete_conversation_data(self, conversation_id: str) -> None:
        """Usuwa zapisane cytaty oraz całą kolekcję wektorową dla danej konwersacji."""
        self._citation_only.pop(conversation_id, None)
        collection_name = self._sanitize_collection_name(conversation_id)

        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception as exc:
            logger.debug("Brak kolekcji '%s' do usunięcia lub błąd: %s", collection_name, exc)

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> list[str]:
        """Dzieli tekst na fragmenty o zadanym nakładaniu, ucinając na granicach słów."""
        clean_text = text.strip()
        if len(clean_text) <= chunk_size:
            return [clean_text] if clean_text else []

        chunks: list[str] = []
        start = 0
        total_len = len(clean_text)

        while start < total_len:
            end = min(start + chunk_size, total_len)

            # Szukanie ostatniej spacji, aby nie rozcinać wyrazów w środku
            if end < total_len:
                last_space = clean_text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            chunk = clean_text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Obliczenie przesunięcia z uwzględnieniem overlapa
            step = max(1, (end - start) - overlap)
            start += step

        return chunks

    @staticmethod
    def _extract_pdf_text(content: bytes) -> str:
        """Wyodrębnia tekst ze strumienia bajtów pliku PDF."""
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text().strip() for page in reader.pages if page.extract_text()]
            return "\n\n".join(pages)
        except Exception as exc:
            logger.error("Błąd podczas parsowania pliku PDF: %s", exc)
            return ""

    @staticmethod
    def _extract_html_text(html: str) -> str:
        """Usuwa zbędne znaczniki strukturalne i zwraca czysty tekst strony."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)

    async def _fetch_text(self, client: httpx.AsyncClient, mtype: str, url: str) -> str | None:
        """Pobiera zasób pod wskazanym adresem i ekstrahuje treść tekstową."""
        try:
            resp = await client.get(url)
            resp.raise_for_status()

            content_type = (resp.headers.get("content-type") or "").lower()
            is_pdf = mtype == "pdf" or "application/pdf" in content_type or url.lower().endswith(".pdf")

            text = self._extract_pdf_text(resp.content) if is_pdf else self._extract_html_text(resp.text)
            return text if text.strip() else None
        except Exception as exc:
            logger.warning("Nie udało się pobrać treści z %s (%s): %s", url, mtype, exc)
            return None

    @staticmethod
    def _build_source_metadata(mat: Any) -> dict[str, Any]:
        """Konwertuje obiekt wejściowy na płaski słownik metadanych ChromaDB."""
        meta: dict[str, Any] = {
            "title": getattr(mat, "title", "Materiał") or "Materiał",
            "url": getattr(mat, "url", "") or "",
            "timestamp": str(getattr(mat, "timestamp", "") or ""),
        }

        raw_page = getattr(mat, "page", None)
        if raw_page not in (None, ""):
            try:
                meta["page"] = int(raw_page)
            except (ValueError, TypeError):
                meta["page"] = str(raw_page)

        return meta

    async def load_materials(self, conversation_id: str, reference_materials: list[Any]) -> None:
        """Pobiera pliki, dzieli na fragmenty i indeksuje embeddingi w kolekcji sesji."""
        self.delete_conversation_data(conversation_id)

        collection_name = self._sanitize_collection_name(conversation_id)
        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_fn,
        )
        self._citation_only[conversation_id] = []

        # Bezpieczna obsługa klienta HTTP bez zamykania wstrzykniętego singletonu
        owned = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=10.0, follow_redirects=True)

        try:
            for mat in reference_materials:
                meta = self._build_source_metadata(mat)
                mtype = getattr(mat, "type", "doc")
                url = meta["url"]

                if mtype == "video_timestamp" or not url.startswith("http"):
                    self._citation_only[conversation_id].append(meta)
                    continue

                if not is_safe_rag_url(url):
                    logger.warning(
                        "Pominięto materiał RAG (niedozwolony URL / SSRF): %s",
                        url,
                    )
                    self._citation_only[conversation_id].append(meta)
                    continue

                text = await self._fetch_text(client, mtype, url)
                if not text:
                    self._citation_only[conversation_id].append(meta)
                    continue

                chunks = self._chunk_text(text)
                if not chunks:
                    continue

                collection.add(
                    documents=chunks,
                    metadatas=[meta] * len(chunks),
                    ids=[str(uuid.uuid4()) for _ in chunks],
                )
        finally:
            if owned:
                aclose = getattr(client, "aclose", None)
                if aclose is not None:
                    await aclose()
                else:
                    # Test doubles often implement async context manager only
                    exit_cm = getattr(client, "__aexit__", None)
                    if exit_cm is not None:
                        await exit_cm(None, None, None)

    def retrieve_context(
        self,
        conversation_id: str,
        question: str,
        lang: str = "pl",
    ) -> tuple[str, list[dict[str, Any]]]:
        """Zwraca scalony kontekst tekstowy dla promptu oraz listę powiązanych źródeł."""
        sources: list[dict[str, Any]] = [
            self._normalize_source_meta(s)
            for s in self._citation_only.get(conversation_id, [])
        ]
        collection_name = self._sanitize_collection_name(conversation_id)

        try:
            collection = self.chroma_client.get_collection(
                name=collection_name,
                embedding_function=self._embedding_fn,
            )
        except Exception:
            return "", sources

        if collection.count() == 0:
            return "", sources

        results = collection.query(query_texts=[question], n_results=RETRIEVE_TOP_K)
        retrieved_chunks: list[str] = (results.get("documents") or [[]])[0]
        metadatas: list[dict[str, Any]] = (results.get("metadatas") or [[]])[0]

        # Deduplikacja źródeł na podstawie adresu URL
        seen_urls = {s["url"] for s in sources if s.get("url")}
        for meta in metadatas:
            if meta and meta.get("url") not in seen_urls:
                seen_urls.add(meta["url"])
                sources.append(self._normalize_source_meta(meta))

        if not retrieved_chunks:
            return "", sources

        header = (
            "FRAGMENTY DOKUMENTACJI Z BAZY WIEDZY:\n"
            if lang == "pl"
            else "DOCUMENTATION SNIPPETS FROM KNOWLEDGE BASE:\n"
        )
        context = header + "\n---\n".join(retrieved_chunks)
        return context, sources

    @staticmethod
    def _normalize_source_meta(meta: dict[str, Any]) -> dict[str, Any]:
        """Formatuje metadane ChromaDB do spójnego schematu wyjściowego API."""
        out = dict(meta)
        raw_page = out.get("page")

        if raw_page in (None, ""):
            out["page"] = None
        else:
            try:
                out["page"] = int(raw_page)
            except (ValueError, TypeError):
                out["page"] = None
        return out

    def chroma_ok(self) -> bool:
        """Weryfikuje dostępność bazy ChromaDB dla mechanizmów healthchecku."""
        try:
            self.chroma_client.heartbeat()
            return True
        except Exception as exc:
            logger.error("Błąd podczas sprawdzania stanu ChromaDB: %s", exc)
            return False