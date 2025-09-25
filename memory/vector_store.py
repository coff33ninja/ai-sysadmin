"Vector-based memory store for semantic recall."

import os
import json
import uuid
from typing import List, Dict, Optional
from datetime import datetime

try:
    import chromadb

    CHROMA_AVAILABLE = True

    # Check ChromaDB version for compatibility
    try:
        CHROMA_VERSION = chromadb.__version__
    except AttributeError:
        CHROMA_VERSION = "unknown"

except ImportError:
    CHROMA_AVAILABLE = False
    chromadb = None
    CHROMA_VERSION = None


class VectorMemory:
    def __init__(self, persist_directory: str = "storage/memory"):
        self.persist_dir = persist_directory
        self.client = None
        self.collection = None
        self.chroma_status = "not_available"

        os.makedirs(persist_directory, exist_ok=True)

        if CHROMA_AVAILABLE:
            try:
                # Try newer ChromaDB API (v0.4+)
                self.client = chromadb.PersistentClient(path=persist_directory)
                self.collection = self.client.get_or_create_collection("ai_memory")
                self.chroma_status = f"persistent_v{CHROMA_VERSION}"
            except AttributeError:
                # Fallback to older ChromaDB API (v0.3.x)
                try:
                    self.client = chromadb.Client(
                        chromadb.config.Settings(
                            chroma_db_impl="duckdb+parquet",
                            persist_directory=persist_directory,
                        )
                    )
                    self.collection = self.client.get_or_create_collection("ai_memory")
                    self.chroma_status = f"legacy_persistent_v{CHROMA_VERSION}"
                except Exception as e:
                    # If both fail, use in-memory client
                    try:
                        self.client = chromadb.Client()
                        self.collection = self.client.get_or_create_collection(
                            "ai_memory"
                        )
                        self.chroma_status = f"memory_only_v{CHROMA_VERSION}"
                    except Exception as e2:
                        print(f"ChromaDB initialization failed: {e2}")
                        self.chroma_status = f"failed: {str(e2)}"

        if not self.collection:
            # Fallback to file-based storage
            self.memory_file = os.path.join(persist_directory, "memories.jsonl")
            self.chroma_status = "file_fallback"

    def get_status(self) -> Dict:
        """Get the current status of the vector memory system."""
        return {
            "chroma_available": CHROMA_AVAILABLE,
            "chroma_version": CHROMA_VERSION,
            "status": self.chroma_status,
            "using_vector_search": self.collection is not None,
            "persist_directory": self.persist_dir,
        }

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


def diagnose_chromadb() -> Dict:
    """Diagnose ChromaDB installation and provide fix suggestions."""
    diagnosis = {"status": "unknown", "issues": [], "suggestions": []}

    if not CHROMA_AVAILABLE:
        diagnosis["status"] = "not_installed"
        diagnosis["issues"].append("ChromaDB is not installed")
        diagnosis["suggestions"].append("Install ChromaDB: pip install chromadb")
        return diagnosis

    # Test different ChromaDB APIs
    apis_tested = []

    # Test PersistentClient (v0.4+)
    try:
        test_client = chromadb.PersistentClient(path="test_temp")
        apis_tested.append("PersistentClient: ✓")
        diagnosis["status"] = "modern_api_working"
    except AttributeError:
        apis_tested.append("PersistentClient: ✗ (not available)")
    except Exception as e:
        apis_tested.append(f"PersistentClient: ✗ ({str(e)})")

    # Test legacy Client (v0.3.x)
    try:
        test_client = chromadb.Client(
            chromadb.config.Settings(
                chroma_db_impl="duckdb+parquet", persist_directory="test_temp"
            )
        )
        apis_tested.append("Legacy Client: ✓")
        if diagnosis["status"] == "unknown":
            diagnosis["status"] = "legacy_api_working"
    except Exception as e:
        apis_tested.append(f"Legacy Client: ✗ ({str(e)})")

    # Test in-memory client
    try:
        test_client = chromadb.Client()
        apis_tested.append("Memory Client: ✓")
        if diagnosis["status"] == "unknown":
            diagnosis["status"] = "memory_only"
    except Exception as e:
        apis_tested.append(f"Memory Client: ✗ ({str(e)})")
        diagnosis["status"] = "all_apis_failed"

    diagnosis["apis_tested"] = apis_tested
    diagnosis["version"] = CHROMA_VERSION

    # Add suggestions based on status
    if diagnosis["status"] == "all_apis_failed":
        diagnosis["suggestions"].extend(
            [
                "Reinstall ChromaDB: pip uninstall chromadb && pip install chromadb",
                "Try a specific version: pip install chromadb==0.4.15",
                "Check for dependency conflicts: pip check",
            ]
        )
    elif diagnosis["status"] == "memory_only":
        diagnosis["suggestions"].append(
            "Persistence not working - data will be lost on restart"
        )
    elif diagnosis["status"] == "legacy_api_working":
        diagnosis["suggestions"].append(
            "Consider upgrading ChromaDB for better performance"
        )

    return diagnosis


def fix_chromadb_installation():
    """Provide interactive fix for ChromaDB issues."""
    print("🔍 Diagnosing ChromaDB installation...")
    diagnosis = diagnose_chromadb()

    print(f"\n📊 Status: {diagnosis['status']}")
    print(f"📦 Version: {diagnosis.get('version', 'unknown')}")

    if diagnosis.get("apis_tested"):
        print("\n🧪 API Tests:")
        for test in diagnosis["apis_tested"]:
            print(f"  {test}")

    if diagnosis.get("issues"):
        print("\n❌ Issues found:")
        for issue in diagnosis["issues"]:
            print(f"  • {issue}")

    if diagnosis.get("suggestions"):
        print("\n💡 Suggestions:")
        for suggestion in diagnosis["suggestions"]:
            print(f"  • {suggestion}")

    return diagnosis


if __name__ == "__main__":
    # Run diagnostics if script is executed directly
    fix_chromadb_installation()
