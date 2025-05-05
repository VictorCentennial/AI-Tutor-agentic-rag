from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Type, Union, Dict, Any
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain.text_splitter import TextSplitter
from langchain_community.document_loaders.base import BaseLoader
from langchain.vectorstores.base import VectorStore
import os

import logging

logger = logging.getLogger(__name__)


class VectorStoreFactory(ABC):
    @abstractmethod
    def create_vector_store(
        self, documents: List[Document], embeddings: Embeddings, **kwargs
    ) -> VectorStore:
        pass

    @abstractmethod
    def load_vector_store(self, *args, **kwargs) -> VectorStore:
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
        collection_name: Optional[str] = None,
        total_weeks: int = 14,
        auto_sync_structure: bool = True,
    ):
        self.embeddings = embeddings
        self.text_splitter = text_splitter
        self.document_loader_factory = document_loader_factory
        self.vector_store_factory = vector_store_factory
        self.documents: Optional[List[Document]] = None
        self.vector_store: Optional[VectorStore] = None
        self.collection_name: Optional[str] = collection_name
        self.total_weeks = total_weeks

        # First load the vector store if use mongodb
        if collection_name:
            self.vector_store = self.load_vector_store()

        # Then sync the course structure if auto_sync is enabled
        if auto_sync_structure and hasattr(
            self.vector_store_factory, "get_course_structure_store"
        ):
            try:
                sync_results = self.sync_course_structure()
                print(
                    f"Course structure synced: added {sync_results['courses_added']} courses, "
                    f"updated {sync_results['weeks_updated']} weeks, "
                    f"added {sync_results['files_added']} files"
                )
            except Exception as e:
                print(f"Warning: Failed to sync course structure: {str(e)}")

    def load_documents(
        self, folder_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Load documents from a folder path with optional metadata.

        Args:
            folder_path: Path to the folder containing documents
            metadata: Optional metadata to add to all documents (e.g., course name, week)

        Returns:
            List of loaded documents
        """
        loader = self.document_loader_factory.create_loader(folder_path)
        self.documents = loader.load()

        # Add metadata to documents if provided
        if metadata and self.documents:
            for doc in self.documents:
                doc.metadata.update(metadata)

        # Add first line as title in metadata
        if self.documents:
            for doc in self.documents:
                if doc.page_content:
                    # # Extract first line and add as title in metadata
                    # first_line = doc.page_content.split("\n")[0].strip()
                    # if first_line:
                    #     doc.metadata["title"] = first_line
                    # Split content into lines
                    lines = doc.page_content.split("\n")
                    title = lines[0].strip()

                    # If title is too short, look for a longer one in the next lines
                    line_index = 1
                    while len(title) < 5 and line_index < len(lines):
                        next_line = lines[line_index].strip()
                        if next_line and len(next_line) >= 5:
                            title = next_line
                            break
                        line_index += 1

                    doc.metadata["title"] = title

        return self.documents

    def embed_documents(self) -> VectorStore:
        """
        Embed documents and store them in the vector store.

        Args:
            collection_name: Optional name for the MongoDB collection (e.g., course name)

        Returns:
            Vector store instance
        """
        if not self.documents:
            raise ValueError("No documents loaded. Call load_documents first.")

        chunks = self.text_splitter.split_documents(self.documents)

        # For MongoDB, pass the collection name
        if self.collection_name:
            self.vector_store = self.vector_store_factory.create_vector_store(
                chunks, self.embeddings, collection_name=self.collection_name
            )
        else:
            self.vector_store = self.vector_store_factory.create_vector_store(
                chunks, self.embeddings
            )

        return self.vector_store

    def load_vector_store(self):
        """
        Load a vector store from a collection.

        Args:
            collection_name: Name of the collection to load

        Returns:
            Loaded vector store
        """
        self.vector_store = self.vector_store_factory.load_vector_store(
            self.collection_name, self.embeddings
        )
        return self.vector_store

    def save_vector_store(self, folder_path: str):
        """
        Save vector store locally (for FAISS compatibility).

        This method is mainly kept for backward compatibility with FAISS.
        MongoDB vector stores don't need to be saved locally as they're
        already persisted in the database.

        Args:
            folder_path: Path to save the vector store
        """
        # Check if the vector store has a save_local method (FAISS)
        if hasattr(self.vector_store, "save_local"):
            self.vector_store.save_local(folder_path)

    # for Local Vector Store
    def get_titles(self, file_name: Optional[str] = None) -> List[str]:
        """
        Get the titles of the documents in the vector store.

        Args:
            file_name (Optional[str], optional): Get the titles of the documents with this file name (extension not included). Defaults to None.

        Raises:
            ValueError: If no vector store is available.
            ValueError: If no documents are loaded.

        Returns:
            List[str]: The titles of the documents in the vector store.
        """

        if self.vector_store:
            # Get titles from vector store
            # For Chroma:
            if hasattr(self.vector_store, "get"):
                docs = self.vector_store.get()
                if file_name:
                    titles_set = set(
                        [
                            doc.page_content.split("\n")[0]
                            for doc in docs["documents"]
                            if os.path.splitext(doc.metadata.get("source", ""))[
                                0
                            ].endswith(file_name)
                        ]
                    )
                else:
                    titles_set = set(
                        [doc.page_content.split("\n")[0] for doc in docs["documents"]]
                    )
            # For FAISS:
            elif hasattr(self.vector_store, "docstore"):
                docs = list(self.vector_store.docstore._dict.values())
                if file_name:
                    titles_set = set(
                        [
                            doc.page_content.split("\n")[0]
                            for doc in docs
                            if os.path.splitext(doc.metadata.get("source", ""))[
                                0
                            ].endswith(file_name)
                        ]
                    )
                else:
                    # for mongodb
                    titles_set = set([doc.page_content.split("\n")[0] for doc in docs])

            else:
                raise ValueError("Unsupported vector store type")
        else:
            raise ValueError("No vector store available")

        return list(titles_set)

    def query_vector_store(
        self,
        query: str,
        k: int = 3,
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """
        Query the vector store for similar documents.

        Args:
            query: Query string
            k: Number of results to return
            collection_name: Optional collection name to query (if not using the current one)

        Returns:
            List of similar documents
        """
        # If collection name is provided and it's different from the current one,
        # load that collection first
        if collection_name and collection_name != self.current_collection:
            self.load_vector_store(collection_name)

        if not self.vector_store:
            raise ValueError(
                "Vector store not initialized. Call embed_documents or load_vector_store first."
            )

        return self.vector_store.similarity_search(query, k=k, **kwargs)

    # function specific to MongoDB

    def get_titles_Mongodb(self, course: str, weeks: list[int]) -> List[str]:
        return self.vector_store_factory.get_titles_Mongodb(
            course, weeks, self.collection_name
        )

    # Collections name is the course name
    def list_collections(self) -> List[str]:
        """
        List all collections in the MongoDB database.

        Returns:
            List of collection names
        """
        if hasattr(self.vector_store_factory, "list_collections"):
            return self.vector_store_factory.list_collections()
        return []

    def delete_collection(self, collection_name: str) -> dict:
        """
        Delete a collection from the database.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if successful
        """
        return self.vector_store_factory.delete_collection(collection_name)

    def delete_by_course(self, course_name: str) -> dict:
        """
        Delete all documents for a given course.

        Args:
            collection_name: Name of the collection to delete
            course_name: Name of the course to delete

        Returns:
            True if successful
        """
        return self.vector_store_factory.delete_by_course(
            self.collection_name, course_name
        )

    def delete_by_week(self, course_name: str, week: int) -> dict:
        """
        Delete all documents for a given course and week.
        """
        return self.vector_store_factory.delete_by_week(
            self.collection_name, course_name, week
        )

    def delete_by_file(self, course_name: str, week: int, file_name: str) -> bool:
        """
        Delete a specific file from the database.
        """
        return self.vector_store_factory.delete_by_file(
            self.collection_name, course_name, week, file_name
        )

    def get_courses(self) -> List[str]:
        """
        Get all courses from the database. Only for courses with documents in the vector store.
        """
        return self.vector_store_factory.get_courses(self.collection_name)

    def get_courses_from_structure(self) -> List[str]:
        """
        Get all courses from the course structure store.
        """
        if hasattr(self.vector_store_factory, "get_course_structure_store"):
            structure_store = self.vector_store_factory.get_course_structure_store()
            return structure_store.get_courses_from_structure()
        else:
            print("Vector store factory does not have a course structure store")
            return []

    def get_course_material_from_structure(
        self, course_name: str
    ) -> Dict[str, str | List[str] | Dict[str, str | List[str]]]:
        """
        Get all course material for a given course from the course structure store.
        """
        if hasattr(self.vector_store_factory, "get_course_structure_store"):
            structure_store = self.vector_store_factory.get_course_structure_store()
            return structure_store.get_course_material_from_structure(course_name)
        else:
            print("Vector store factory does not have a course structure store")
            return {}

    def get_course_material(self, course_name: str) -> Dict[str, List[str]]:
        """
        Get all course material for a given course in the form of a dictionary with week numbers as keys and lists of file names as values.
        """
        return self.vector_store_factory.get_course_material(
            self.collection_name, course_name, self.total_weeks
        )

    def add_course_to_structure(self, course_name: str) -> Dict[str, Any]:
        """
        Add a course to the course structure store.
        """
        if hasattr(self.vector_store_factory, "get_course_structure_store"):
            structure_store = self.vector_store_factory.get_course_structure_store()
            return structure_store.add_course_to_structure(course_name)
        else:
            print("Vector store factory does not have a course structure store")
            return {
                "message": "Vector store factory does not have a course structure store"
            }

    def set_week_topic(self, course_name: str, week: int, topic_name: str) -> bool:
        """
        Set the topic name for a specific week in the course structure store.
        """
        if hasattr(self.vector_store_factory, "get_course_structure_store"):
            structure_store = self.vector_store_factory.get_course_structure_store()
            return structure_store.set_week_topic(course_name, week, topic_name)
        else:
            print("Vector store factory does not have a course structure store")
            return {
                "message": "Vector store factory does not have a course structure store"
            }

    def get_topics(self, course_name: str) -> Dict[int, str]:
        """
        Temporary return weeks as topics
        TODO: Implement topics with user defined names
        """
        if hasattr(self.vector_store_factory, "get_course_structure_store"):
            structure_store = self.vector_store_factory.get_course_structure_store()
            print("Vector store factory has a course structure store")
            topics = {}
            for week in range(1, self.total_weeks + 1):
                topic = structure_store.get_week_topic(course_name, week)
                if topic:
                    topics[week] = topic
            return topics
        else:
            print("Vector store factory does not have a course structure store")
            return {}

    def delete_course_material(
        self, course_name: str, week: int, file_name: str
    ) -> bool:
        """
        Delete course material from the database.
        """
        return self.vector_store_factory.delete_course_material(
            self.collection_name, course_name, week, file_name
        )

    def delete_course(self, course_name: str) -> bool:
        """
        Delete a course from the database.
        """
        return self.vector_store_factory.delete_course(
            self.collection_name, course_name
        )

    def load_from_folder_path_to_mongodb_vector_store(
        self, course_name: str, week: int, folder_path: str
    ) -> bool:
        """
        Load files from a folder path to the vector store.
        """
        metadata = {
            "course": course_name,
            "week": week,
        }

        logger.info(f"Loading documents from {folder_path} to MongoDB vector store")

        documents = self.load_documents(folder_path, metadata)

        logger.info(f"Documents loaded")

        return self.vector_store_factory.load_from_folder_path_to_mongodb_vector_store(
            self.vector_store, course_name, week, documents
        )

    def sync_course_structure(self) -> Dict[str, Any]:
        """
        Synchronize the course structure store with the current vector store.

        Returns:
            Dictionary with sync results
        """
        # Check if we have a MongoDB vector store factory with a course structure store
        if hasattr(self.vector_store_factory, "get_course_structure_store"):
            structure_store = self.vector_store_factory.get_course_structure_store()
            return structure_store.sync_with_rag(self)
        else:
            return {
                "error": "Vector store factory does not have a course structure store",
                "courses_added": 0,
                "weeks_updated": 0,
                "files_added": 0,
            }

    def edit_week_topic(self, course_name: str, week: int, topic_name: str) -> bool:
        """
        Edit the topic name for a specific week in the course structure store.
        """
        return self.vector_store_factory.edit_week_topic(course_name, week, topic_name)
