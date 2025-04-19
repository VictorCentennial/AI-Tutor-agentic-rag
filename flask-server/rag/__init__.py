from langchain.text_splitter import CharacterTextSplitter
from rag.FAISS_vector_stores import (
    FAISSVectorStoreFactory,
)
from rag.MongoDB_vector_stores import MongoDBVectorStoreFactory
from rag.Document_loader import (
    PDFDirectoryLoaderFactory,
    MultiDocumentDirectoryLoaderFactory,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from rag.RAG import RAG
import os
from config import TOTAL_WEEKS

load_dotenv()

# Initialize dependencies
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)

# Choose which vector store to use
use_mongodb = os.environ.get("USE_MONGODB", "true").lower() == "true"
VectorStoreDatabaseName = os.environ.get("MongoDBVectorStoreDatabaseName")

if use_mongodb:
    # Use MongoDB vector store
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError(
            "MONGODB_URI environment variable is required when using MongoDB vector store"
        )

    vector_store_factory = MongoDBVectorStoreFactory(
        connection_string=mongodb_uri, db_name=VectorStoreDatabaseName
    )
else:
    # Use FAISS vector store (local)
    vector_store_factory = FAISSVectorStoreFactory()

# Use multi-document loader for various file types
document_loader_factory = MultiDocumentDirectoryLoaderFactory()

if use_mongodb:
    collection_name = os.environ.get("MongoDBCollectionName") or "course_materials"
else:
    collection_name = None

# Create RAG instance
rag = RAG(
    embeddings=embeddings,
    text_splitter=text_splitter,
    document_loader_factory=document_loader_factory,
    vector_store_factory=vector_store_factory,
    collection_name=collection_name,
    total_weeks=TOTAL_WEEKS,
)
