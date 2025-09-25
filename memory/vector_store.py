try:
    import chromadb
    from chromadb.config import Settings
    _CHROMADB_AVAILABLE = True
except Exception:
    chromadb = None
    _CHROMADB_AVAILABLE = False


class VectorStore:
    def __init__(self, persist_path: str = "storage/vector_store"):
        self.persist_path = persist_path
        self.client = None
        self.collection = None
        if _CHROMADB_AVAILABLE:
            self.client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=self.persist_path))
            try:
                self.collection = self.client.get_collection("ai_memory")
            except Exception:
                self.collection = self.client.create_collection("ai_memory")

    def remember(self, text: str, metadata: dict = None, id: str = None):
        if not _CHROMADB_AVAILABLE:
            return {"error": "chromadb not installed"}
        _id = id or str(hash(text))
        self.collection.add(documents=[text], metadatas=[metadata or {}], ids=[_id])
        self.client.persist()
        return {"id": _id}

    def recall(self, query: str, n_results: int = 3):
        if not _CHROMADB_AVAILABLE:
            return {"error": "chromadb not installed"}
        res = self.collection.query(query_texts=[query], n_results=n_results)
        return res
