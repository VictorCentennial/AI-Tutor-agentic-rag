import logging
from typing import Collection
from aiTutorAgent.AiTutorAgent import AiTutorAgent
from langchain_core.messages import AIMessage, HumanMessage
from bson.binary import Binary
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatHistoryMongoDB:
    def __init__(self, checkpoint_collection: Collection, aiTutorAgent: AiTutorAgent):
        self.checkpoint_collection = checkpoint_collection
        self.aiTutorAgent = aiTutorAgent

    def get_all_threads(self) -> list[str]:
        return self.checkpoint_collection.distinct("thread_id")

    def get_all_student_ids(self) -> list[str]:
        raw_student_ids = self.checkpoint_collection.distinct("metadata.user_id")
        student_ids = [
            self.binary_decoding(student_id) for student_id in raw_student_ids
        ]
        logger.info(f"student_ids: {student_ids}")
        return student_ids

    def get_chat_history_by_student_id(self, student_id: str) -> list[dict]:

        # 1) Aggregate to get every unique (binary_user, thread_id) pair
        pipeline = [
            {"$group": {"_id": {"user": "$metadata.user_id", "thread": "$thread_id"}}},
            {"$project": {"_id": 0, "user": "$_id.user", "thread": "$_id.thread"}},
        ]
        cursor = self.checkpoint_collection.aggregate(pipeline)

        # 2) Decode and pick only this student's threads
        thread_ids: list[str] = []
        for entry in cursor:
            raw_user = entry.get("user")  # a bson.Binary
            decoded = self.binary_decoding(raw_user).strip('"')
            if decoded == student_id:
                thread_ids.append(entry.get("thread"))

        logger.info(
            f"Total {len(thread_ids)} thread_ids for {student_id} are: {thread_ids}"
        )

        conversations = []
        for thread_id in thread_ids:
            try:
                # Create thread config
                thread_config = {
                    "configurable": {"thread_id": thread_id, "user_id": str(student_id)}
                }

                # Try to get state - this will succeed if the thread belongs to this user
                # Otherwise, it will raise an exception
                state = self.aiTutorAgent.graph.get_state(thread_config)

                stored_user_id = state.metadata.get("user_id")
                # print(f"stored_user_id: {stored_user_id}")
                # print(f"student_id: {student_id}")
                if stored_user_id != student_id:
                    # Skip this thread – it doesn't belong to the given student
                    continue

                # Extract conversation information
                messages = state.values.get("messages", [])

                conversation = {
                    "thread_id": thread_id,
                    "subject": state.values.get("subject", "Unknown"),
                    "created_at": state.created_at,
                    "messages": self.messages_to_json(messages),
                    "message_count": len(messages),
                }

                # Add additional metadata if available
                if state.metadata:
                    conversation["step"] = state.metadata.get("step", 0)

                conversations.append(conversation)

            except Exception as e:
                # This thread doesn't belong to this user
                logger.debug(f"Thread {thread_id} retrival error: {str(e)}")
                continue

        # Sort conversations by creation date (newest first)
        conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return conversations

    def get_chat_history_by_course_code(self, course_code: str) -> list[dict]:
        # Get all threads
        thread_ids = self.get_all_threads()
        logger.info(f"Total {len(thread_ids)} threads found for course code search")

        conversations = []
        for thread_id in thread_ids:
            try:
                # We don't know the user_id upfront, so we'll need to check each thread's subject
                # Get all user_ids for this thread
                user_docs = self.checkpoint_collection.find(
                    {"thread_id": thread_id}, {"metadata.user_id": 1}
                )

                user_ids = set()
                for doc in user_docs:
                    if "metadata" in doc and "user_id" in doc["metadata"]:
                        raw_user = doc["metadata"]["user_id"]
                        decoded = self.binary_decoding(raw_user).strip('"')
                        user_ids.add(decoded)

                # Try each user_id until we find a valid one
                found_valid_state = False
                for user_id in user_ids:
                    try:
                        thread_config = {
                            "configurable": {
                                "thread_id": thread_id,
                                "user_id": str(user_id),
                            }
                        }

                        state = self.aiTutorAgent.graph.get_state(thread_config)

                        # Check if this conversation has the right course code
                        subject = state.values.get("subject", "")
                        if (
                            subject
                            and subject.split("_")[0].strip().upper()
                            == course_code.upper()
                        ):
                            # Extract conversation information
                            messages = state.values.get("messages", [])

                            conversation = {
                                "thread_id": thread_id,
                                "subject": subject,
                                "created_at": state.created_at,
                                "messages": self.messages_to_json(messages),
                                "message_count": len(messages),
                                "user_id": user_id,
                            }

                            # Add additional metadata if available
                            if state.metadata:
                                conversation["step"] = state.metadata.get("step", 0)

                            conversations.append(conversation)
                            found_valid_state = True
                            break  # Found a valid state for this thread, no need to try other user_ids
                    except Exception as e:
                        # This thread with this user_id is not valid, try the next one
                        logger.debug(
                            f"Thread {thread_id} with user_id {user_id} error: {str(e)}"
                        )
                        continue

                if not found_valid_state:
                    logger.debug(f"No valid state found for thread {thread_id}")

            except Exception as e:
                logger.debug(f"Error processing thread {thread_id}: {str(e)}")
                continue

        # Sort conversations by creation date (newest first)
        conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return conversations

    def get_chat_history_by_date(self, date: str) -> list[dict]:
        # Get all threads
        thread_ids = self.get_all_threads()
        logger.info(f"Total {len(thread_ids)} threads found for date search")

        conversations = []
        for thread_id in thread_ids:
            try:
                # We don't know the user_id upfront, so we'll need to try to access each thread
                # Get all user_ids for this thread
                user_docs = self.checkpoint_collection.find(
                    {"thread_id": thread_id}, {"metadata.user_id": 1}
                )

                user_ids = set()
                for doc in user_docs:
                    if "metadata" in doc and "user_id" in doc["metadata"]:
                        raw_user = doc["metadata"]["user_id"]
                        decoded = self.binary_decoding(raw_user).strip('"')
                        user_ids.add(decoded)

                # Try each user_id until we find a valid one
                found_valid_state = False
                for user_id in user_ids:
                    try:
                        thread_config = {
                            "configurable": {
                                "thread_id": thread_id,
                                "user_id": str(user_id),
                            }
                        }

                        state = self.aiTutorAgent.graph.get_state(thread_config)

                        # Check if this conversation has the right date
                        start_time = state.values.get("start_time", "")
                        logger.info(f"start_time: {start_time}")
                        logger.info(f"type of start_time: {type(start_time)}")

                        # Handle both string and datetime formats
                        if start_time:
                            conversation_date = ""
                            if isinstance(start_time, datetime):
                                # Format datetime object to YYYYMMDD format
                                conversation_date = start_time.strftime("%Y%m%d")
                            elif isinstance(start_time, str) and "T" in start_time:
                                # Handle ISO format string (YYYY-MM-DDTHH:MM:SS)
                                conversation_date = start_time.split("T")[0].replace(
                                    "-", ""
                                )

                            logger.info(f"conversation_date: {conversation_date}")
                            logger.info(f"date: {date}")

                            if conversation_date == date:
                                # Extract conversation information
                                messages = state.values.get("messages", [])

                                conversation = {
                                    "thread_id": thread_id,
                                    "subject": state.values.get("subject", "Unknown"),
                                    "created_at": state.created_at,
                                    "messages": self.messages_to_json(messages),
                                    "message_count": len(messages),
                                    "user_id": user_id,
                                }

                                # Add additional metadata if available
                                if state.metadata:
                                    conversation["step"] = state.metadata.get("step", 0)

                                conversations.append(conversation)
                                found_valid_state = True
                                break  # Found a valid state for this thread, no need to try other user_ids
                    except Exception as e:
                        # This thread with this user_id is not valid, try the next one
                        logger.debug(
                            f"Thread {thread_id} with user_id {user_id} error: {str(e)}"
                        )
                        continue

                if not found_valid_state:
                    logger.debug(f"No valid state found for thread {thread_id}")

            except Exception as e:
                logger.debug(f"Error processing thread {thread_id}: {str(e)}")
                continue

        # Sort conversations by creation date (newest first)
        conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return conversations

    def get_chat_history_all(self) -> list[dict]:
        # Get all threads
        thread_ids = self.get_all_threads()
        logger.info(f"Total {len(thread_ids)} threads found")

        conversations = []
        for thread_id in thread_ids:
            try:
                # We don't know the user_id upfront, so we'll need to try to access each thread
                # Get all user_ids for this thread
                user_docs = self.checkpoint_collection.find(
                    {"thread_id": thread_id}, {"metadata.user_id": 1}
                )

                user_ids = set()
                for doc in user_docs:
                    if "metadata" in doc and "user_id" in doc["metadata"]:
                        raw_user = doc["metadata"]["user_id"]
                        decoded = self.binary_decoding(raw_user).strip('"')
                        user_ids.add(decoded)

                # Try each user_id until we find a valid one
                found_valid_state = False
                for user_id in user_ids:
                    try:
                        thread_config = {
                            "configurable": {
                                "thread_id": thread_id,
                                "user_id": str(user_id),
                            }
                        }

                        state = self.aiTutorAgent.graph.get_state(thread_config)

                        # Extract conversation information
                        messages = state.values.get("messages", [])

                        conversation = {
                            "thread_id": thread_id,
                            "subject": state.values.get("subject", "Unknown"),
                            "created_at": state.created_at,
                            "messages": self.messages_to_json(messages),
                            "message_count": len(messages),
                            "user_id": user_id,
                        }

                        # Add additional metadata if available
                        if state.metadata:
                            conversation["step"] = state.metadata.get("step", 0)

                        conversations.append(conversation)
                        found_valid_state = True
                        break  # Found a valid state for this thread, no need to try other user_ids
                    except Exception as e:
                        # This thread with this user_id is not valid, try the next one
                        logger.debug(
                            f"Thread {thread_id} with user_id {user_id} error: {str(e)}"
                        )
                        continue

                if not found_valid_state:
                    logger.debug(f"No valid state found for thread {thread_id}")

            except Exception as e:
                logger.debug(f"Error processing thread {thread_id}: {str(e)}")
                continue

        # Sort conversations by creation date (newest first)
        conversations.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return conversations

    def get_all_session_data(self) -> list[dict]:
        """
        Retrieve all session data including date, time, course_code, and student_id from the collections.

        Returns:
            list[dict]: A list of dictionaries, each containing session metadata
        """
        # Get all threads
        thread_ids = self.get_all_threads()
        logger.info(f"Total {len(thread_ids)} threads found for session data retrieval")

        session_data = []
        for thread_id in thread_ids:
            try:
                # Get all user_ids for this thread
                user_docs = self.checkpoint_collection.find(
                    {"thread_id": thread_id}, {"metadata.user_id": 1}
                )

                user_ids = set()
                for doc in user_docs:
                    if "metadata" in doc and "user_id" in doc["metadata"]:
                        raw_user = doc["metadata"]["user_id"]
                        decoded = self.binary_decoding(raw_user).strip('"')
                        user_ids.add(decoded)

                # Try each user_id until we find a valid one
                for user_id in user_ids:
                    try:
                        thread_config = {
                            "configurable": {
                                "thread_id": thread_id,
                                "user_id": str(user_id),
                            }
                        }

                        state = self.aiTutorAgent.graph.get_state(thread_config)

                        # Extract the subject (course code)
                        subject = state.values.get("subject", "Unknown")
                        course_code = (
                            subject.split("_")[0] if "_" in subject else subject
                        )

                        # Extract start time
                        start_time = state.values.get("start_time", "")

                        # Format the date and time
                        date = ""
                        time = ""
                        if isinstance(start_time, datetime):
                            date = start_time.strftime("%Y%m%d")
                            time = start_time.strftime("%H%M")
                        elif isinstance(start_time, str) and "T" in start_time:
                            date_part = start_time.split("T")[0].replace("-", "")
                            time_part = (
                                start_time.split("T")[1]
                                .split(".")[0]
                                .replace(":", "")[:4]
                            )
                            date = date_part
                            time = time_part

                        # Create session data entry
                        session_entry = {
                            "thread_id": thread_id,
                            "date": date,
                            "time": time,
                            "course_code": course_code,
                            "student_id": user_id,
                            "subject": subject,
                        }

                        # Add additional metadata if available
                        if state.metadata:
                            session_entry["step"] = state.metadata.get("step", 0)

                        session_data.append(session_entry)
                        break  # Found a valid state for this thread, no need to try other user_ids

                    except Exception as e:
                        # This thread with this user_id is not valid, try the next one
                        logger.debug(
                            f"Thread {thread_id} with user_id {user_id} error: {str(e)}"
                        )
                        continue

            except Exception as e:
                logger.debug(f"Error processing thread {thread_id}: {str(e)}")
                continue

        # Sort by date and time (newest first)
        session_data.sort(
            key=lambda x: (x.get("date", ""), x.get("time", "")), reverse=True
        )

        return session_data

    def save_chat_history(self, user_id: str, course_id: str, chat_history: list[dict]):
        pass

    def messages_to_json(self, messages):
        """
        Convert a list of LangChain messages to JSON format.

        Args:
            messages (list): A list of AIMessage and HumanMessage objects.

        Returns:
            str: A JSON string representing the list of messages.
        """
        messages_json = [
            (
                {"role": "ai", "content": message.content}
                if isinstance(message, AIMessage)
                else {"role": "student", "content": message.content}
            )
            for message in messages
        ]
        return messages_json

    def binary_decoding(self, binary_data):
        """
        Decode binary data to a string.
        """
        raw = binary_data.decode("utf-8")
        return raw.strip("'").strip('"')
