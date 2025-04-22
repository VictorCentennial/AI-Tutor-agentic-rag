# import sqlite3
# from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import os
from aiTutorAgent.AiTutorAgent import AiTutorAgent
from pymongo import MongoClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
import atexit
from pymongo.errors import ConnectionFailure
import logging
from rag import rag

logging.getLogger("pymongo").setLevel(logging.INFO)

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL_NAME = os.getenv(
    "GOOGLE_MODEL_NAME", "gemini-1.5-pro-latest"
)  # Use "gemini-pro" or your model name

# MongoDB connection settings
logging.info(f"MONGODB_URI environment variable: {os.environ.get('MONGODB_URI')}")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
if not MONGODB_URI or not (
    MONGODB_URI.startswith("mongodb://") or MONGODB_URI.startswith("mongodb+srv://")
):
    logging.error(f"Invalid MONGODB_URI: {MONGODB_URI}")
    raise ValueError("Invalid MONGODB_URI")

MONGODB_DB = os.getenv("MONGODB_DB", "ai_tutor_db")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "agent_checkpoints")


# Create MongoDB client
mongodb_client = MongoClient(MONGODB_URI)

try:
    mongodb_client.admin.command("ismaster")
    print("✅ MongoDB connection successful!")
    # print(f"   URI: {MONGODB_URI}")
    # print(f"   Database: {MONGODB_DB}")
    # print(f"   Collection: {MONGODB_COLLECTION}")
except ConnectionFailure as e:
    print(f"❌ MongoDB connection failed: {e}")
    mongodb_client = None

# Initialize MongoDB checkpointer with specific db and collection
memory = MongoDBSaver(
    client=mongodb_client,
    db_name=MONGODB_DB,
    checkpoint_collection_name=MONGODB_COLLECTION,
)

# memory = SqliteSaver(conn=sqlite3.connect(":memory:", check_same_thread=False))
# memory = MemorySaver()

vector_store = None
# For mongodb vector store
use_mongodb = os.environ.get("USE_MONGODB", "true").lower() == "true"

if use_mongodb:
    # vector store is already loaded in rag instance
    vector_store = rag.vector_store


aiTutorAgent = AiTutorAgent(
    GOOGLE_MODEL_NAME=GOOGLE_MODEL_NAME,
    GOOGLE_API_KEY=GOOGLE_API_KEY,
    memory=memory,
    vector_store=vector_store,
)


# Register cleanup function to close MongoDB connection
def close_mongodb_connection():
    if mongodb_client:
        mongodb_client.close()
        print("MongoDB connection closed")


atexit.register(close_mongodb_connection)
