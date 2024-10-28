import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import os
from aiTutorAgent.AiTutorAgent import AiTutorAgent

from langgraph.checkpoint.memory import MemorySaver

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL_NAME = os.getenv(
    "GOOGLE_MODEL_NAME", "gemini-pro"
)  # Use "gemini-pro" or your model name

# memory = SqliteSaver(conn=sqlite3.connect(":memory:", check_same_thread=False))
memory = MemorySaver()
aiTutorAgent = AiTutorAgent(
    GOOGLE_MODEL_NAME=GOOGLE_MODEL_NAME, GOOGLE_API_KEY=GOOGLE_API_KEY, memory=memory
)
