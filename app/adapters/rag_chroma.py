import logging
import uuid
from typing import Any

import chromadb
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RagService:
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self._citation_only: dict[str, list[dict[str, Any]]] = {}

    def _collection_name(self, conversation_id: str) -> str:
        # ChromaDB requires letters, digits, underscores (no hyphens)
        safe_id = conversation_id.replace("-", "_")
        return f"pja_kb_{safe_id}"

    def delete_conversation_data(self, conversation_id: str) -> None:
        """Drop in-memory citations and Chroma collection for a conversation."""
        self._citation_only.pop(conversation_id, None)
        collection_name = self._collection_name(conversation_id)
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        if len(text) <= chunk_size:
            return [text] if text else []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    async def load_materials(self, conversation_id: str, reference_materials: list):
        """Fetch HTML docs into Chroma; keep pdf/slide/video as citation metadata only."""
        collection_name = self._collection_name(conversation_id)
        self.delete_conversation_data(conversation_id)

        collection = self.chroma_client.get_or_create_collection(name=collection_name)
        self._citation_only[conversation_id] = []

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as http_client:
            for material in reference_materials:
                source_meta = {
                    "title": getattr(material, "title", "Material"),
                    "url": getattr(material, "url", ""),
                    "timestamp": getattr(material, "timestamp", None),
                    "page": getattr(material, "page", None),
                }

                if getattr(material, "type", "") in ("pdf", "video_timestamp", "slide"):
                    self._citation_only[conversation_id].append(
                        {k: v for k, v in source_meta.items() if v is not None}
                    )
                    continue

                if getattr(material, "type", "") == "doc" and source_meta["url"].startswith("http"):
                    try:
                        resp = await http_client.get(source_meta["url"])
                        resp.raise_for_status()
                        soup = BeautifulSoup(resp.text, "html.parser")
                        text = soup.get_text(separator=" ", strip=True)

                        chunks = self._chunk_text(text, chunk_size=500, overlap=60)
                        if not chunks:
                            continue

                        ids = [str(uuid.uuid4()) for _ in chunks]
                        metadatas = [
                            {
                                "title": source_meta["title"],
                                "url": source_meta["url"],
                                "timestamp": str(source_meta["timestamp"] or ""),
                                "page": str(source_meta["page"] or ""),
                            }
                            for _ in chunks
                        ]
                        collection.add(documents=chunks, metadatas=metadatas, ids=ids)
                    except Exception as e:
                        logger.warning(
                            "Failed to load RAG material %s: %s", source_meta["url"], e
                        )

    def retrieve_context(
        self, conversation_id: str, question: str, lang: str = "pl"
    ) -> tuple[str, list[dict[str, Any]]]:
        sources: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for src in self._citation_only.get(conversation_id, []):
            url = src.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append(dict(src))

        collection_name = self._collection_name(conversation_id)
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
        except Exception:
            return "", sources

        if collection.count() == 0:
            return "", sources

        results = collection.query(query_texts=[question], n_results=3)

        if not results.get("documents") or not results["documents"][0]:
            return "", sources

        retrieved_chunks = results["documents"][0]
        metadatas = (results.get("metadatas") or [[]])[0] or []

        for meta in metadatas:
            if not meta:
                continue
            url = meta.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                entry: dict[str, Any] = {
                    "title": meta.get("title") or "Material",
                    "url": url,
                }
                if meta.get("timestamp"):
                    entry["timestamp"] = meta["timestamp"]
                if meta.get("page"):
                    try:
                        entry["page"] = int(meta["page"])
                    except (TypeError, ValueError):
                        pass
                sources.append(entry)

        header = (
            "DOCUMENTATION SNIPPETS FROM KNOWLEDGE BASE:\n"
            if lang == "en"
            else "FRAGMENTY DOKUMENTACJI Z BAZY WEKTOROWEJ DO WYKORZYSTANIA:\n"
        )
        context = f"{header}" + "\n---\n".join(retrieved_chunks)
        return context, sources

    def chroma_ok(self) -> bool:
        try:
            self.chroma_client.heartbeat()
            return True
        except Exception:
            try:
                _ = self.chroma_client.list_collections()
                return True
            except Exception:
                return False
