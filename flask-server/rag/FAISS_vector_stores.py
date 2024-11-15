from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader
from rag.RAG import VectorStoreFactory, DocumentLoaderFactory
from typing import List
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore
from langchain.document_loaders.base import BaseLoader
from langchain_community.document_loaders import PyPDFLoader


class FAISSVectorStoreFactory(VectorStoreFactory):
    def create_vector_store(
        self, documents: List[Document], embeddings: Embeddings
    ) -> VectorStore:
        return FAISS.from_documents(documents, embeddings)


class PDFDirectoryLoaderFactory(DocumentLoaderFactory):
    def create_loader(self, folder_path: str) -> BaseLoader:
        return DirectoryLoader(folder_path, glob="*.pdf", loader_cls=PyPDFLoader)
