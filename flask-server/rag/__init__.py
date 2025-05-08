print("Starting RAG initialization...")
from dotenv import load_dotenv

load_dotenv()
print("load_dotenv completed")

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
from rag.RAG import RAG
import os
from config import TOTAL_WEEKS

print("import completed")

# Initialize dependencies
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)

# Choose which vector store to use
use_mongodb = os.environ.get("USE_MONGODB", "true").lower() == "true"
VectorStoreDatabaseName = os.environ.get("MongoDBVectorStoreDatabaseName")

print("VectorStoreDatabaseName: ", VectorStoreDatabaseName)
print("use_mongodb: ", use_mongodb)

if use_mongodb:
    # Use MongoDB vector store
    mongodb_uri = os.environ.get("MONGODB_URI")
    print("mongodb_uri: ", mongodb_uri)

    if not mongodb_uri:
        raise ValueError(
            "MONGODB_URI environment variable is required when using MongoDB vector store"
        )
    try:
        vector_store_factory = MongoDBVectorStoreFactory(
            connection_string=mongodb_uri, db_name=VectorStoreDatabaseName
        )
    except Exception as e:
        print("Error creating MongoDB vector store: ", e)

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
