from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch
from rag.RAG import VectorStoreFactory, DocumentLoaderFactory
from typing import List, Union, Dict, Any, Optional
from pathlib import Path
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore
from pymongo import MongoClient
import os
from bson import ObjectId
import re


class MongoDBVectorStoreFactory(VectorStoreFactory):
    """
    Factory for creating and loading MongoDB Atlas Vector Search instances.
    """

    def __init__(self, connection_string: str = None, db_name: str = "ai_tutor_rag_db"):
        """
        Initialize the MongoDB Vector Store Factory.

        Args:
            connection_string: MongoDB connection string (if None, will try to get from environment)
            db_name: Name of the database to use
        """
        self.connection_string = connection_string or os.environ.get("MONGODB_URI")
        if not self.connection_string:
            raise ValueError(
                "MongoDB connection string not provided and not found in environment"
            )

        self.db_name = db_name
        self.client = MongoClient(self.connection_string)

    def create_vector_store(
        self,
        documents: List[Document],
        embeddings: Embeddings,
        collection_name: str = "default",
    ) -> VectorStore:
        """
        Create a new MongoDB Atlas Vector Search instance from documents.

        Args:
            documents: List of documents to store
            embeddings: Embeddings model to use
            collection_name: Name of the collection to use (can be course name)

        Returns:
            MongoDB Atlas Vector Search instance
        """
        # Extract metadata to determine collection name if needed

        # if (
        #     documents
        #     and hasattr(documents[0], "metadata")
        #     and "course" in documents[0].metadata
        # ):
        #     # Use the course name as collection name if available
        #     course_name = documents[0].metadata["course"]
        #     # Clean the collection name (remove special characters)
        collection_name = "".join(e for e in collection_name if e.isalnum() or e == "_")

        # Get the database and collection
        db = self.client[self.db_name]
        collection = db[collection_name]

        # Create vector store
        vector_store = MongoDBAtlasVectorSearch.from_documents(
            documents,
            embeddings,
            collection=collection,
            index_name=f"{collection_name[:8]}_vector_index",
        )

        vector_store.create_vector_search_index(
            dimensions=768,  # The dimensions of the vector embeddings to be indexed
            filters=["week"],
        )

        return vector_store

    def load_vector_store(
        self,
        collection_name: str,
        embeddings: Embeddings,
    ) -> VectorStore:
        """
        Load a MongoDB Atlas Vector Search instance.

        Args:
            collection_name: Name of the collection to use
            embeddings: Embeddings model to use

        Returns:
            MongoDB Atlas Vector Search instance
        """
        db = self.client[self.db_name]
        collection = db[collection_name]

        # Load existing vector store
        vector_store = MongoDBAtlasVectorSearch(
            collection=collection,
            embedding=embeddings,
            # Sanitize the index name to remove invalid characters and limit length
            index_name=self._sanitize_index_name(f"{collection_name}_vector_index"),
            text_key="text",
        )

        vector_store.create_vector_search_index(
            dimensions=768,  # The dimensions of the vector embeddings to be indexed
            filters=["course", "week"],
        )

        return vector_store

    def list_collections(self) -> List[str]:
        """
        List all collections (courses) in the database.

        Returns:
            List of collection names
        """
        db = self.client[self.db_name]
        return db.list_collection_names()

    def delete_collection(self, collection_name: str) -> dict:
        """
        Delete a collection from the database.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            MongoDB operation result dictionary or error message
        """
        db = self.client[self.db_name]

        # Check if collection exists before attempting to delete
        if collection_name in db.list_collection_names():
            result = db[collection_name].drop()
            return {"acknowledged": True, "result": result}
        else:
            print(f"Collection '{collection_name}' does not exist")
            return {
                "acknowledged": False,
                "error": f"Collection '{collection_name}' does not exist",
            }

    def delete_by_course(self, collection_name: str, course_name: str) -> dict:
        """
        Delete all documents for a specific course.

        Args:
            collection_name (str): Name of the collection to delete from
            course_name (str): Course material's documents to be deleted

        Returns:
            dict: MongoDB delete operation result
        """
        db = self.client[self.db_name]
        collection = db[collection_name]
        result = collection.delete_many({"course": course_name})
        return {
            "acknowledged": result.acknowledged,
            "deleted_count": result.deleted_count,
        }

    def delete_by_week(self, collection_name: str, course_name: str, week: int) -> dict:
        """
        Delete course material for a specific week.

        Args:
            collection_name (str): Name of the collection
            course_name (str): Course to delete from
            week (int): Week number to delete

        Returns:
            dict: MongoDB delete operation result
        """
        db = self.client[self.db_name]
        collection = db[collection_name]
        result = collection.delete_many({"course": course_name, "week": week})
        return {
            "acknowledged": result.acknowledged,
            "deleted_count": result.deleted_count,
        }

    def delete_by_file(
        self, collection_name: str, course_name: str, week: int, file_name: str
    ) -> dict:
        """
        Delete course material for a specific file.

        Args:
            collection_name (str): Name of the collection
            course_name (str): Course to delete from
            week (int): Week number
            file_name (str): Name of the file to delete

        Returns:
            dict: MongoDB delete operation result
        """
        try:
            db = self.client[self.db_name]
            collection = db[collection_name]
            result = collection.delete_many(
                {"course": course_name, "week": week, "filename": file_name}
            )
            return {
                "acknowledged": result.acknowledged,
                "deleted_count": result.deleted_count,
            }
        except Exception as e:
            print(f"Error deleting file: {e}")
            return {"acknowledged": False, "error": str(e)}

    def get_titles_Mongodb(
        self, course: str, weeks: list[int], collection_name: str
    ) -> List[str]:
        """
        Get titles from MongoDB for a specific course and week.

        Args:
            course(str): Name of the course
            weeks (list[int]): List of weeks to filter
            collection_name (str): Name of the collection

        Returns:
            List of titles
        """
        db = self.client[self.db_name]
        collection = db[collection_name]

        print(f"course: {course}")
        print(f"weeks: {weeks}")
        print(f"collection_name: {collection_name}")

        titles = []
        for week in weeks:
            print(f"week: {week}")
            titles_in_week = collection.find(
                {"course": course, "week": int(week)}
            ).distinct("title")
            print(f"titles_in_week: {titles_in_week}")
            titles.extend(titles_in_week)
        print(f"titles: {titles}")
        return titles

    def get_courses(self, collection_name: str) -> List[str]:
        """
        Get all courses from the database.
        """
        db = self.client[self.db_name]
        collection = db[collection_name]
        return collection.distinct("course")

    def get_course_material(
        self, collection_name: str, course_name: str, total_weeks: int
    ) -> Dict[str, List[str]]:
        """
        Get all course material for a given course.
        """
        db = self.client[self.db_name]
        collection = db[collection_name]
        course_materials_by_week = {}
        for week in range(1, total_weeks + 1):
            course_materials_by_week[week] = collection.distinct(
                "filename", {"course": course_name, "week": week}
            )
        return course_materials_by_week

    def delete_course_material(
        self,
        collection_name: str,
        course_name: str,
        week: int,
        file_name: str,
    ) -> bool:
        """
        Delete course material from the database.
        """
        db = self.client[self.db_name]
        collection = db[collection_name]
        collection.delete_many(
            {"course": course_name, "week": week, "filename": file_name}
        )
        return True

    def delete_course(self, collection_name: str, course_name: str) -> bool:
        """
        Delete a course from the database.
        """
        db = self.client[self.db_name]
        collection = db[collection_name]
        collection.delete_many({"course": course_name})
        return True

    # Add this method to your class
    def _sanitize_index_name(self, name: str) -> str:
        """
        Sanitize index name to ensure it's valid for MongoDB.

        Args:
            name: The proposed index name

        Returns:
            A sanitized index name valid for MongoDB
        """
        # Remove spaces and special characters
        sanitized = re.sub(r"[^\w_]", "", name)

        # Ensure it's not too long (MongoDB has limits, 127 bytes is safe)
        if len(sanitized) > 20:  # Use a conservative limit
            # Keep the beginning and end parts with a separator
            sanitized = sanitized[:7]

        return sanitized
