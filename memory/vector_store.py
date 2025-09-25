"Vector-based memory store for semantic recall."

import os
import json
import uuid
from typing import List, Dict, Optional
from datetime import datetime

try:
    import chromadb

    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    chromadb = None


class VectorMemory:
    def __init__(self, persist_directory: str = "storage/memory"):
        self.persist_dir = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        if CHROMA_AVAILABLE:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection("ai_memory")
        else:
            # Fallback to file-based storage
            self.collection = None
            self.memory_file = os.path.join(persist_directory, "memories.jsonl")

    def remember(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Store a memory with optional metadata."""
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        if metadata is None:
            metadata = {}

        metadata.update({"timestamp": timestamp, "id": memory_id})

        if self.collection:
            # Use ChromaDB for vector storage
            self.collection.add(documents=[text], metadatas=[metadata], ids=[memory_id])
        else:
            # Fallback to JSONL file
            memory_record = {"id": memory_id, "text": text, "metadata": metadata}
            with open(self.memory_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(memory_record) + "\n")

        return memory_id

    def recall(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Retrieve memories similar to the query."""
        if self.collection:
            # Semantic search with ChromaDB
            results = self.collection.query(
                query_texts=[query], n_results=limit, where=filter_metadata
            )

            memories = []
            if results and results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    memories.append(
                        {
                            "id": results["ids"][0][i],
                            "text": results["documents"][0][i],
                            "distance": results["distances"][0][i],
                            "metadata": results["metadatas"][0][i],
                        }
                    )
            return memories
        else:
            # Fallback to simple text matching
            memories = self._load_all_memories()
            query_lower = query.lower()

            # Simple relevance scoring based on word overlap
            scored = []
            for memory in memories:
                text_lower = memory["text"].lower()
                words_query = set(query_lower.split())
                words_text = set(text_lower.split())
                overlap = len(words_query.intersection(words_text))
                if overlap > 0:
                    scored.append((overlap / len(words_query), memory))

            # Sort by relevance and return top results
            scored.sort(reverse=True, key=lambda x: x[0])
            return [item[1] for item in scored[:limit]]

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent memories by timestamp."""
        memories = self._load_all_memories()
        # Sort by timestamp descending
        memories.sort(key=lambda x: x["metadata"].get("timestamp", ""), reverse=True)
        return memories[:limit]

    def _load_all_memories(self) -> List[Dict]:
        """Load all memories from file (fallback method)."""
        if not os.path.exists(self.memory_file):
            return []

        memories = []
        with open(self.memory_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    memories.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return memories


# Global instance
_memory_store = None


def get_memory_store() -> VectorMemory:
    """Get the global memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = VectorMemory()
    return _memory_store


def remember(text: str, metadata: Optional[Dict] = None) -> str:
    """Store a memory."""
    return get_memory_store().remember(text, metadata)

def recall(query: str, limit: int = 5) -> List[Dict]:
    """Recall memories similar to query."""
    return get_memory_store().recall(query, limit)

def get_recent_memories(limit: int = 10) -> List[Dict]:
    """Get recent memories."""
    return get_memory_store().get_recent(limit)
