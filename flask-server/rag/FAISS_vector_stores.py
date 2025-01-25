from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader
from rag.RAG import VectorStoreFactory, DocumentLoaderFactory
from typing import List, Union
from pathlib import Path
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore
from langchain.document_loaders.base import BaseLoader
from langchain_community.document_loaders import PyPDFLoader
import logging


class FAISSVectorStoreFactory(VectorStoreFactory):
    def create_vector_store(
        self, documents: List[Document], embeddings: Embeddings
    ) -> VectorStore:
        return FAISS.from_documents(documents, embeddings)

    def load_vector_store(
        self,
        folder_paths: Union[str, List[str], Path, List[Path]],
        embeddings: Embeddings,
    ) -> VectorStore:
        """
        Load one or multiple vector stores and merge them if necessary.

        Args:
            folder_paths: Single path or list of paths to FAISS index folders
            embeddings: Embeddings model to use

        Returns:
            FAISS vector store (merged if multiple paths provided)

        Raises:
            ValueError: If no valid folder paths are provided
        """
        # Convert to list if single path
        if isinstance(folder_paths, (str, Path)):
            folder_paths = [folder_paths]

        if not folder_paths:
            raise ValueError("No folder paths provided")

        # Load the first vector store
        merged_store = FAISS.load_local(
            str(folder_paths[0]), embeddings, allow_dangerous_deserialization=True
        )

        # Merge additional vector stores if they exist
        for path in folder_paths[1:]:
            store = FAISS.load_local(
                str(path), embeddings, allow_dangerous_deserialization=True
            )
            merged_store.merge_from(store)
            logging.info(f"Merged vector store from {path}")

        return merged_store

    # def load_vector_store(
    #     self, folder_path: str, embeddings: Embeddings
    # ) -> VectorStore:
    #     return FAISS.load_local(
    #         folder_path, embeddings, allow_dangerous_deserialization=True
    #     )

    # def load_and_merge_vector_stores(
    #     self, folder_paths: List[str], embeddings: Embeddings
    # ) -> VectorStore:
    #     """
    #     Load multiple vector stores and merge them into one.

    #     Args:
    #         folder_paths: List of paths to FAISS index folders
    #         embeddings: Embeddings model to use

    #     Returns:
    #         Merged FAISS vector store
    #     """
    #     if not folder_paths:
    #         raise ValueError("No folder paths provided")

    #     # Load the first vector store
    #     merged_store = FAISS.load_local(
    #         folder_paths[0], embeddings, allow_dangerous_deserialization=True
    #     )

    #     # Merge the remaining vector stores
    #     for path in folder_paths[1:]:
    #         store = FAISS.load_local(
    #             path, embeddings, allow_dangerous_deserialization=True
    #         )
    #         merged_store.merge_from(store)

    #     return merged_store


class PDFDirectoryLoaderFactory(DocumentLoaderFactory):
    def create_loader(self, folder_path: str) -> BaseLoader:
        return DirectoryLoader(folder_path, glob="*.pdf", loader_cls=PyPDFLoader)
