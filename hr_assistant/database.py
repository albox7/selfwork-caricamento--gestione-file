# database.py
import chromadb
from chromadb.utils import embedding_functions
from config import Config


class Database:
    def __init__(self):
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=Config.OPENAI_KEY, model_name=Config.MODEL_NAME
        )

        self.client = chromadb.PersistentClient(path=Config.PERSISTENT_DIR)
        self._init_collection()

    def _init_collection(self):
        self.collection = self.client.get_or_create_collection(
            name=Config.COLLECTION_NAME, embedding_function=self.openai_ef
        )

    def delete_collection(self):
        self.client.delete_collection(Config.COLLECTION_NAME)
        self._init_collection()

    def add_documents(self, documents, metadatas, ids):
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def query(self, query_text, n_results=1):
        return self.collection.query(query_texts=[query_text], n_results=n_results)

    def get_tracked_files(self):
        result = self.collection.get()
        tracked_files = {}

        if result and result["metadatas"]:
            for metadata in result["metadatas"]:
                if metadata["source"] not in tracked_files:
                    tracked_files[metadata["source"]] = {
                        "hash": metadata["hash"],
                        "last_modified": metadata["last_modified"],
                        "source": metadata["source"],
                    }

        return tracked_files

    def remove_document_by_source(self, source):
        result = self.collection.get(where={"source": source})
        if result and result["ids"]:
            self.collection.delete(ids=result["ids"])

    def get_stats(self):
        result = self.collection.get()
        valori_distinti = set(d["source"] for d in result["metadatas"])
        numero_files = len(valori_distinti)

        return f"""
            Nome Collezione: {self.collection.name}
            Numero totale Frammenti: {self.collection.count()}
            Numero Files Elaborati: {numero_files}
        """