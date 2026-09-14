"""Adapter RAG: ChromaDB + pobieranie materiałów referencyjnych (HTML/PDF)."""

import io
import logging
import re
import uuid
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 60
RETRIEVE_TOP_K = 3


class RagService:
    """Indeksuje materiały per sesja i zwraca top-k fragmentów do promptu LLM."""

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        chroma_client: chromadb.ClientAPI | None = None,
    ) -> None:
        self.chroma_client = chroma_client or chromadb.Client()
        self._http_client = http_client
        # Materiały bez treści do embedowania (np. video_timestamp) — tylko cytowanie.
        self._citation_only: dict[str, list[dict[str, Any]]] = {}

        self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    @staticmethod
    def _sanitize_collection_name(conversation_id: str) -> str:
        """Nazwa kolekcji Chroma zgodna z ograniczeniami alfanumerycznymi (max 63)."""
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", conversation_id)
        return f"pja_kb_{safe_id}"[:63]

    def delete_conversation_data(self, conversation_id: str) -> None:
        """Usuwa cytowania i kolekcję wektorową powiązaną z sesją."""
        self._citation_only.pop(conversation_id, None)
        collection_name = self._sanitize_collection_name(conversation_id)
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception as exc:
            logger.debug("Brak kolekcji %s do usunięcia lub błąd: %s", collection_name, exc)

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
    ) -> list[str]:
        """Dzieli tekst na nakładające się fragmenty, preferując granice spacji."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            
            if end < text_len:
                boundary = text.rfind(" ", start, end)
                if boundary > start:
                    end = boundary

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            step = max(1, (end - start) - overlap)
            start += step

        return chunks

    @staticmethod
    def _extract_pdf_text(content: bytes) -> str:
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join(
                page_text.strip()
                for page in reader.pages
                if (page_text := page.extract_text())
            )
        except Exception as exc:
            logger.error("Błąd dekodowania pliku PDF: %s", exc)
            return ""

    @staticmethod
    def _extract_html_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)

    async def _fetch_text(self, client: httpx.AsyncClient, mtype: str, url: str) -> str | None:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()

            is_pdf = mtype == "pdf" or "application/pdf" in content_type or url.lower().endswith(".pdf")
            if is_pdf:
                text = self._extract_pdf_text(resp.content)
            else:
                text = self._extract_html_text(resp.text)

            return text if text.strip() else None
        except Exception as exc:
            logger.warning("Nie udało się pobrać treści z %s (%s): %s", url, mtype, exc)
            return None

    async def load_materials(self, conversation_id: str, reference_materials: list[Any]) -> None:
        """Pobiera URL-e materiałów, chunkuje treść i zapisuje embeddingi w Chroma."""
        collection_name = self._sanitize_collection_name(conversation_id)
        self.delete_conversation_data(conversation_id)

        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_fn,
        )
        self._citation_only[conversation_id] = []

        async with (self._http_client or httpx.AsyncClient(timeout=10.0, follow_redirects=True)) as client:
            for mat in reference_materials:
                raw_page = getattr(mat, "page", None)
                try:
                    page = int(raw_page) if raw_page not in (None, "") else None
                except (TypeError, ValueError):
                    page = str(raw_page) if raw_page not in (None, "") else None
                meta = {
                    "title": getattr(mat, "title", "Materiał"),
                    "url": getattr(mat, "url", ""),
                    "timestamp": str(getattr(mat, "timestamp", "") or ""),
                }
                # Chroma metadata must be non-null scalars; only store page when known.
                if isinstance(page, int):
                    meta["page"] = page
                elif page not in (None, ""):
                    meta["page"] = str(page)
                mtype = getattr(mat, "type", "doc")
                url = meta["url"]

                if mtype == "video_timestamp" or not url.startswith("http"):
                    self._citation_only[conversation_id].append(meta)
                    continue

                text = await self._fetch_text(client, mtype, url)
                if not text:
                    self._citation_only[conversation_id].append(meta)
                    continue

                chunks = self._chunk_text(text)
                if not chunks:
                    continue

                ids = [str(uuid.uuid4()) for _ in chunks]
                metadatas = [meta for _ in chunks]
                collection.add(documents=chunks, metadatas=metadatas, ids=ids)

    def retrieve_context(
        self, conversation_id: str, question: str, lang: str = "pl"
    ) -> tuple[str, list[dict[str, Any]]]:
        """Zwraca blok kontekstu RAG oraz listę źródeł (w tym citation-only)."""
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
        retrieved_chunks = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]

        seen_urls = {s["url"] for s in sources if "url" in s}
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
        """Map Chroma metadata to API SourceRef shape (empty page → None)."""
        out = dict(meta)
        raw_page = out.get("page", None)
        if raw_page in (None, ""):
            out.pop("page", None)
            out["page"] = None
        else:
            try:
                out["page"] = int(raw_page)
            except (TypeError, ValueError):
                out["page"] = None
        return out

    def chroma_ok(self) -> bool:
        """Sonda gotowości ChromaDB dla endpointu /health."""
        try:
            self.chroma_client.heartbeat()
            return True
        except Exception as exc:
            logger.error("Błąd podczas sprawdzania stanu ChromaDB: %s", exc)
            return False