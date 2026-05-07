# document_processor.py
import os
import uuid
import hashlib
from typing import Tuple, List, Dict, Any
from config import Config
from semantic_chunking import SemanticChunking
from markitdown import MarkItDown
from zipfile import ZipFile
import tempfile
import mimetypes


class DocumentProcessor:
    SUPPORTED_EXTENSIONS = {
        ".txt": "text",
        ".pdf": "document",
        ".doc": "document",
        ".docx": "document",
        ".ppt": "presentation",
        ".pptx": "presentation",
        ".xls": "spreadsheet",
        ".xlsx": "spreadsheet",
        ".html": "web",
        ".htm": "web",
        ".csv": "data",
        ".json": "data",
        ".xml": "data",
        ".zip": "archive",
    }

    def __init__(self):
        self.md_converter = MarkItDown()

    @staticmethod
    def read_first_lines(file_path: str, n_lines: int = 100) -> List[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return [line.strip() for line, _ in zip(file, range(n_lines))]
        except UnicodeDecodeError:
            return []

    @staticmethod
    def get_file_hash(file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

   
    def get_document_metadata(self, file_path: str) -> Dict[str, Any]:
        extension = os.path.splitext(file_path)[1].lower()
        file_type = self.SUPPORTED_EXTENSIONS.get(extension, "unknown")

        metadata = {
            "hash": self.get_file_hash(file_path),
            "last_modified": os.path.getmtime(file_path),
            "source": os.path.basename(file_path),
            "file_type": file_type,
            "mime_type": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
            "extension": extension,
        }
        # ChromaDB accetta solo str/int/float/bool nei metadati: filtriamo per sicurezza
        return {
            k: v for k, v in metadata.items()
            if isinstance(v, (str, int, float, bool))
        }


    def _process_zip_file(self, file_path: str) -> List[Tuple[str, str]]:
        results = []
        with tempfile.TemporaryDirectory() as temp_dir:
            with ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        inner_path = os.path.join(root, file)
                        if os.path.splitext(file)[1].lower() in self.SUPPORTED_EXTENSIONS:
                            content = self._convert_to_markdown(inner_path)
                            if content:
                                results.append((file, content))
        return results

    def _convert_to_markdown(self, file_path: str) -> str:
        try:
            result = self.md_converter.convert(file_path)
            return result.text_content
        except Exception as e:
            print(f"Error converting {file_path}: {str(e)}")
            return ""

    def process_single_document(self, file_path: str) -> Tuple[List[str], List[Dict], List[str]]:
        documents = []
        metadatas = []
        ids = []

        extension = os.path.splitext(file_path)[1].lower()
        file_type = self.SUPPORTED_EXTENSIONS.get(extension)

        if not file_type:
            return [], [], []

        content = ""
        if file_type == "archive":
            zip_contents = self._process_zip_file(file_path)
            for filename, zip_content in zip_contents:
                if zip_content:
                    content += f"\n\nFile: {filename}\n{zip_content}"
        else:
            content = self._convert_to_markdown(file_path)

        if content:
            sc = SemanticChunking(Config.AI_API_KEY, 65, 3)
            chunks = sc.chunk_text(content)
            file_metadata = self.get_document_metadata(file_path)

            for chunk in chunks:
                if not chunk.isspace() and not chunk == "":
                    documents.append(chunk)
                    metadatas.append(file_metadata)
                    ids.append(str(uuid.uuid4()))

        return documents, metadatas, ids

    def process_documents(self, db) -> Tuple[int, int, int]:
        current_files = {
            f: self.get_document_metadata(os.path.join(Config.DOCUMENTS_DIR, f))
            for f in os.listdir(Config.DOCUMENTS_DIR)
            if os.path.splitext(f)[1].lower() in self.SUPPORTED_EXTENSIONS
        }

        existing_files = db.get_tracked_files()

        files_to_add = set(current_files.keys()) - set(existing_files.keys())
        files_to_remove = set(existing_files.keys()) - set(current_files.keys())

        files_to_update = {
            f
            for f in set(current_files.keys()) & set(existing_files.keys())
            if current_files[f]["hash"] != existing_files[f]["hash"]
        }

        for action, files in [("add", files_to_add), ("update", files_to_update)]:
            for filename in files:
                file_path = os.path.join(Config.DOCUMENTS_DIR, filename)
                documents, metadatas, ids = self.process_single_document(file_path)

                if action == "update":
                    db.remove_document_by_source(filename)

                if documents:
                    db.add_documents(documents, metadatas, ids)

        for filename in files_to_remove:
            db.remove_document_by_source(filename)

        return len(files_to_add), len(files_to_update), len(files_to_remove)