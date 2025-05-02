import logging
from typing import Collection
from aiTutorAgent.AiTutorAgent import AiTutorAgent
from langchain_core.messages import AIMessage, HumanMessage
from bson.binary import Binary

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

    def get_chat_history(self, student_id: str) -> list[dict]:
        # thread_ids = self.get_all_threads()

        # user_bin = Binary(student_id.encode("utf-8"), subtype=0)

        # # Query for only this student's checkpoints (projecting thread_id)
        # cursor = self.checkpoint_collection.find(
        #     {"metadata.user_id": user_bin}, {"thread_id": 1}
        # )
        # # Gather unique thread IDs without using distinct()
        # thread_ids = {doc["thread_id"] for doc in cursor}
        # thread_ids = self.checkpoint_collection.distinct(
        #     "thread_id", {"metadata.user_id": user_bin}
        # )

        # logger.info(
        #     f"thread_ids for {student_id} with user_bin: {user_bin} are: {thread_ids}"
        # )

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
