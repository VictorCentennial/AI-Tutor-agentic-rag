from langchain_community.vectorstores import FAISS
from rag.RAG import VectorStoreFactory
from typing import List, Union
from pathlib import Path
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore


# from langchain_community.document_loaders import PyPDFLoader

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
