from __future__ import annotations
from pathlib import Path
import chromadb
from chromadb.config import Settings


class MemoryStore:
    def __init__(self, chroma_dir: Path):
        chroma_dir = Path(chroma_dir)
        chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._notion = self._client.get_or_create_collection("notion_chunks")
        self._history = self._client.get_or_create_collection("conversation_history")
        self._files = self._client.get_or_create_collection("file_index")

    def upsert_notion_chunk(
        self,
        chunk_id: str,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        self._notion.upsert(ids=[chunk_id], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def search_notion(
        self, query: str, embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        count = self._notion.count()
        if count == 0:
            return []
        result = self._notion.query(query_embeddings=[embedding], n_results=min(top_k, count))
        return self._format_results(result)

    def upsert_turn(self, turn_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self._history.upsert(ids=[turn_id], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def search_history(self, query: str, embedding: list[float], top_k: int = 10) -> list[dict]:
        count = self._history.count()
        if count == 0:
            return []
        result = self._history.query(query_embeddings=[embedding], n_results=min(top_k, count))
        return self._format_results(result)

    def upsert_file_chunk(self, chunk_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self._files.upsert(ids=[chunk_id], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def search_files(self, embedding: list[float], top_k: int = 5) -> list[dict]:
        count = self._files.count()
        if count == 0:
            return []
        result = self._files.query(query_embeddings=[embedding], n_results=min(top_k, count))
        return self._format_results(result)

    def _format_results(self, result: dict) -> list[dict]:
        ids = result["ids"][0]
        docs = result["documents"][0]
        metas = result["metadatas"][0]
        dists = result.get("distances", [[]])[0]
        out = []
        for i, doc_id in enumerate(ids):
            entry = {"id": doc_id, "text": docs[i], **(metas[i] or {})}
            if dists:
                entry["score"] = 1 - dists[i]
            out.append(entry)
        return out
