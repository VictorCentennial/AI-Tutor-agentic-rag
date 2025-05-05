import pymongo
from typing import List, Dict, Optional, Any
from config import TOTAL_WEEKS
from dataclasses import dataclass
import logging
import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    filename: str
    last_modified: str


class CourseStructureStore:
    def __init__(self, connection_string: str, db_name: str = "course_structure"):
        self.client = pymongo.MongoClient(connection_string)
        self.db = self.client[db_name]
        self.collection = self.db["course_structure"]

        # Create indexes for faster queries
        self.collection.create_index([("course_name", pymongo.ASCENDING)])

    def sync_with_rag(self, rag_instance) -> Dict[str, Any]:
        """
        Synchronize the course structure store with the RAG instance.
        Adds any missing courses, weeks, and files from the vector store to the structure store.

        Args:
            rag_instance: The RAG instance that contains the vector store information

        Returns:
            Dictionary with sync results statistics
        """
        results = {
            "courses_added": 0,
            "weeks_updated": 0,
            "files_added": 0,
            "errors": [],
        }

        logger.info("=" * 40)
        logger.info("STARTING COURSE STRUCTURE SYNC")
        logger.info("=" * 40)

        try:
            # Check if RAG has a vector_store
            logger.info(
                f"RAG has vector store: {rag_instance.vector_store is not None}"
            )
            logger.info(f"RAG collection name: {rag_instance.collection_name}")

            # Get all courses from RAG
            logger.info("Fetching courses from RAG...")
            courses = rag_instance.get_courses()
            logger.info(f"Courses returned from RAG: {courses}")

            if not courses:
                logger.warning(
                    "No courses found in vector store. Collection may be empty."
                )

                # Let's check what collections exist in MongoDB
                if hasattr(rag_instance.vector_store_factory, "list_collections"):
                    collections = rag_instance.vector_store_factory.list_collections()
                    logger.info(f"Available collections in MongoDB: {collections}")

                # Check what's in the course structure already
                existing_courses = self.get_courses_from_structure()
                logger.info(f"Existing courses in structure store: {existing_courses}")

                return results

            # Process each course
            for course_name in courses:
                logger.info(f"Processing course: {course_name}")

                # Check if course exists in structure store
                existing_course = self.collection.find_one({"course_name": course_name})
                logger.info(
                    f"Course exists in structure: {existing_course is not None}"
                )

                if not existing_course:
                    logger.info(f"Adding course to structure: {course_name}")
                    course_id = self.add_course_to_structure(course_name)
                    logger.info(f"Course added with ID: {course_id}")
                    results["courses_added"] += 1

                # Get course material organized by week from RAG
                logger.info(f"Fetching course material for {course_name}...")
                course_material = rag_instance.get_course_material(course_name)
                logger.info(f"Course material: {course_material}")

                # Check if we have any material
                if not course_material:
                    logger.warning(f"No course material found for {course_name}")
                    continue

                # Process each week with content
                for week_str, filenames in course_material.items():
                    logger.info(f"Processing week {week_str} with files: {filenames}")

                    if not filenames:
                        logger.info(f"Week {week_str} has no files, skipping")
                        continue

                    try:
                        week = int(week_str)
                    except ValueError:
                        logger.error(f"Invalid week format: {week_str}")
                        continue

                    # Get existing files for this week
                    logger.info(
                        f"Fetching existing files for {course_name}, week {week}"
                    )
                    week_data = self.get_week_material_from_structure(course_name, week)
                    logger.info(f"Existing week data: {week_data}")

                    # Extract existing filenames
                    existing_files = set()
                    for item in week_data.get("files", []):
                        if isinstance(item, dict) and "filename" in item:
                            existing_files.add(item["filename"])
                        elif isinstance(item, FileInfo):
                            existing_files.add(item.filename)

                    logger.info(f"Existing files in week {week}: {existing_files}")

                    # Find new files
                    new_files = []
                    for filename in filenames:
                        if filename not in existing_files:
                            logger.info(f"New file found: {filename}")
                            file_info = FileInfo(
                                filename=filename,
                                last_modified="",
                            )
                            new_files.append(file_info)

                    logger.info(f"New files to add: {len(new_files)}")

                    # If we have new files, add them to structure
                    if new_files:
                        logger.info(f"Updating week {week} with new files")

                        # Convert existing material to FileInfo objects
                        existing_file_infos = []
                        for item in week_data.get("files", []):
                            if isinstance(item, dict) and "filename" in item:
                                existing_file_infos.append(
                                    FileInfo(
                                        filename=item["filename"],
                                        last_modified=item.get("last_modified", ""),
                                    )
                                )
                            elif isinstance(item, FileInfo):
                                existing_file_infos.append(item)

                        # Combine existing and new files
                        all_files = existing_file_infos + new_files
                        logger.info(f"Total files after merge: {len(all_files)}")

                        # Try to update the structure
                        try:
                            success = self.add_week_material_to_structure(
                                course_name, week, all_files
                            )
                            logger.info(f"Update successful: {success}")

                            if success:
                                results["weeks_updated"] += 1
                                results["files_added"] += len(new_files)
                            else:
                                logger.warning(
                                    f"Failed to update week {week} for course {course_name}"
                                )
                        except Exception as e:
                            logger.error(f"Error updating week material: {str(e)}")
                            results["errors"].append(f"Week update error: {str(e)}")
                    else:
                        logger.info(f"No new files to add for week {week}")

            logger.info(f"Sync complete with results: {results}")

        except Exception as e:
            error_msg = f"Error in sync_with_rag: {str(e)}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

            # Print stack trace for debugging
            import traceback

            logger.error(traceback.format_exc())

        logger.info("=" * 40)
        logger.info("COMPLETED COURSE STRUCTURE SYNC")
        logger.info("=" * 40)

        return results

    def add_course_to_structure(
        self, course_name: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a new course to the structure store"""
        existing = self.collection.find_one({"course_name": course_name})
        if existing:
            return {
                "success": False,
                "message": "Course already exists in structure store",
                "course_id": str(existing["_id"]),
            }

        # Initialize an empty structure for all weeks
        weeks = {}
        for week in range(1, TOTAL_WEEKS + 1):
            weeks[str(week)] = {
                "topic_name": "",  # Default topic name
                "files": [],  # Empty files list
            }

        course_data = {
            "course_name": course_name,
            "description": description,
            "weeks": weeks,
            "created_at": datetime.datetime.now(),
        }

        result = self.collection.insert_one(course_data)
        return {
            "success": True,
            "message": "Course added to structure store",
            "course_id": str(result.inserted_id),
        }

    def add_week_material_to_structure(
        self, course_name: str, week: int, files: List[FileInfo]
    ) -> bool:
        """Add materials for a specific week in a course"""
        # Convert FileInfo objects to dictionaries
        file_dicts = [
            {"filename": file.filename, "last_modified": file.last_modified}
            for file in files
        ]

        result = self.collection.update_one(
            {"course_name": course_name},
            {"$push": {f"weeks.{week}.files": {"$each": file_dicts}}},
        )
        return result.modified_count > 0

    def add_file_to_structure(
        self, course_name: str, week: int, file_info: FileInfo
    ) -> bool:
        """Add a single file to a week's materials"""
        file_info_dict = {
            "filename": file_info.filename,
            "last_modified": file_info.last_modified,
        }
        result = self.collection.update_one(
            {"course_name": course_name}, {"$push": {f"weeks.{week}": file_info_dict}}
        )
        return result.modified_count > 0

    def get_courses_from_structure(self) -> List[str]:
        """Get all course names"""
        courses = self.collection.find({}, {"course_name": 1})
        return [course["course_name"] for course in courses]

    def get_course_material_from_structure(
        self, course_name: str
    ) -> Dict[str, List[Dict]]:
        """Get all materials for a course organized by week"""
        course = self.collection.find_one({"course_name": course_name})
        if not course:
            return {}
        return course.get("weeks", {})

    def get_week_material_from_structure(self, course_name: str, week: int) -> Dict:
        """Get materials for a specific week"""
        course = self.collection.find_one({"course_name": course_name})
        if not course or "weeks" not in course:
            return {"topic_name": "", "files": []}

        week_data = course["weeks"].get(str(week), {"topic_name": "", "files": []})
        return week_data

    def remove_file_from_structure(
        self, course_name: str, week: int, file_name: str
    ) -> bool:
        """Remove a file from a week's materials"""
        result = self.collection.update_one(
            {"course_name": course_name},
            {"$pull": {f"weeks.{week}.files": {"filename": file_name}}},
        )
        return result.modified_count > 0

    def delete_course_from_structure(self, course_name: str) -> bool:
        """Delete an entire course"""
        result = self.collection.delete_one({"course_name": course_name})
        return result.deleted_count > 0

    def set_week_topic(self, course_name: str, week: int, topic_name: str) -> bool:
        """Set the topic name for a specific week"""
        result = self.collection.update_one(
            {"course_name": course_name},
            {"$set": {f"weeks.{week}.topic_name": topic_name}},
        )
        return result.modified_count > 0

    def get_week_topic(self, course_name: str, week: int) -> str:
        """Get the topic name for a specific week"""
        course = self.collection.find_one({"course_name": course_name})
        if not course or "weeks" not in course:
            return ""
        return course.get("weeks", {}).get(str(week), {}).get("topic_name", "")

    def remove_week_material_from_structure(self, course_name: str, week: int) -> bool:
        """Remove all materials for a specific week"""
        result = self.collection.update_one(
            {"course_name": course_name},
            {"$set": {f"weeks.{week}": {"topic_name": "", "files": []}}},
        )
        return result.modified_count > 0

    def edit_week_topic(self, course_name: str, week: int, topic_name: str) -> bool:
        """Edit the topic name for a specific week"""
        result = self.collection.update_one(
            {"course_name": course_name},
            {"$set": {f"weeks.{week}.topic_name": topic_name}},
        )
        return result.modified_count > 0
