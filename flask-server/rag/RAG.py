from abc import ABC, abstractmethod
from typing import List, Optional, Type
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain.text_splitter import TextSplitter
from langchain_community.document_loaders.base import BaseLoader
from langchain.vectorstores.base import VectorStore


class VectorStoreFactory(ABC):
    @abstractmethod
    def create_vector_store(
        self, documents: List[Document], embeddings: Embeddings
    ) -> VectorStore:
        pass


class DocumentLoaderFactory(ABC):
    @abstractmethod
    def create_loader(self, folder_path: str) -> BaseLoader:
        pass


class RAG:
    def __init__(
        self,
        embeddings: Embeddings,
        text_splitter: TextSplitter,
        document_loader_factory: DocumentLoaderFactory,
        vector_store_factory: VectorStoreFactory,
    ):
        self.embeddings = embeddings
        self.text_splitter = text_splitter
        self.document_loader_factory = document_loader_factory
        self.vector_store_factory = vector_store_factory
        self.documents: Optional[List[Document]] = None
        self.vector_store: Optional[VectorStore] = None

    def load_documents(self, folder_path: str) -> List[Document]:
        loader = self.document_loader_factory.create_loader(folder_path)
        self.documents = loader.load()
        return self.documents

    def embed_documents(self) -> VectorStore:
        if not self.documents:
            raise ValueError("No documents loaded. Call loaddocuments first.")

        chunks = self.text_splitter.split_documents(self.documents)
        self.vector_store = self.vector_store_factory.create_vector_store(
            chunks, self.embeddings
        )
        return self.vector_store

    def load_vector_store(self, folder_path: str):
        self.vector_store = self.vector_store_factory.load_vector_store(folder_path)
        return self.vector_store

    def get_titles(self) -> List[str]:
        titles_set = set(
            [document.page_content.split("\n")[0] for document in self.documents]
        )
        return list(titles_set)

    def query_vector_store(self, query: str, k: int = 3) -> List[Document]:
        if not self.vector_store:
            raise ValueError(
                "Vector store not initialized. Call embed_documents first."
            )

        return self.vector_store.similarity_search(query, k=k)
