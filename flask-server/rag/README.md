# MongoDB Atlas Vector Search Integration for AI Tutor RAG

This module provides an implementation for using MongoDB Atlas Vector Search as the vector store for the AI Tutor RAG (Retrieval Augmented Generation) system.

## Features

- Store embedded documents in MongoDB Atlas
- Organize course content into separate collections
- Query across courses or within specific courses
- Add metadata to documents (course, week, instructor, etc.)
- Maintain the same API as the original FAISS implementation

## Prerequisites

1. A MongoDB Atlas account (a free tier account works for testing)
2. A MongoDB Atlas cluster with Vector Search enabled
3. Python 3.7+ and required packages

## Setup Instructions

### 1. Create a MongoDB Atlas Account and Cluster

1. Sign up for a free MongoDB Atlas account at [https://www.mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register)
2. Create a new cluster (the free tier M0 is sufficient for testing)
3. Set up network access to allow connections from your IP address
4. Create a database user with read/write permissions

### 2. Enable Vector Search

1. In your Atlas dashboard, go to your cluster
2. Click on the "Search" tab
3. Click "Create Search Index"
4. Select "Vector Search" index type and follow the prompts

You can also create the index programmatically from the code, which is what our implementation does.

### 3. Get Your Connection String

1. In your Atlas dashboard, click "Connect" on your cluster
2. Choose "Connect your application"
3. Copy the connection string and replace `<password>` with your database user's password

### 4. Set Environment Variables

Create a `.env` file in your project root with:

```
MONGODB_URI=your_mongodb_connection_string
USE_MONGODB=true
```

## Usage Examples

### Basic Usage

```python
from rag import rag
from dotenv import load_dotenv

load_dotenv()

# Load documents with metadata
metadata = {
    "course": "Introduction to AI",
    "week": "Week 1",
    "instructor": "Dr. Smith"
}
docs = rag.load_documents("./data/course_materials", metadata=metadata)

# Embed into MongoDB collection named after the course
rag.embed_documents(collection_name="Introduction_to_AI")

# Query the vector store
results = rag.query_vector_store("What are neural networks?", k=3)
for result in results:
    print(result.page_content)
    print(result.metadata)
```

### Working with Multiple Courses

```python
# List all collections (courses) in the database
collections = rag.list_collections()
print(f"Available courses: {collections}")

# Query a specific course
rag.load_vector_store("Machine_Learning_Basics")
results = rag.query_vector_store("What is supervised learning?", k=2)
```

See the `examples` directory for more comprehensive examples.

## Architecture

The implementation consists of:

1. `MongoDB_vector_stores.py`: Contains the `MongoDBVectorStoreFactory` class
2. Enhanced `RAG.py`: Extended to support MongoDB collections
3. Updated `__init__.py`: Configures which vector store to use

## How It Works

1. **Document Loading**: Documents are loaded with metadata including course and week
2. **Embedding**: Documents are embedded and stored in MongoDB collections
3. **Indexing**: A vector search index is created for each collection
4. **Retrieval**: Vector similarity search is used to find relevant documents

## Comparison with FAISS

| Feature | MongoDB Atlas | FAISS |
|---------|--------------|-------|
| Storage | Cloud-based | Local file system |
| Scalability | High | Limited by memory |
| Persistence | Automatic | Manual save/load |
| Collections | Multiple | Single index |
| Metadata filtering | Supported | Limited |
| Cost | Potential costs for large data | Free (local only) |

## References

- [MongoDB Atlas Vector Search RAG Documentation](https://www.mongodb.com/docs/atlas/atlas-vector-search/rag/)
- [LangChain MongoDBAtlasVectorSearch](https://python.langchain.com/docs/integrations/vectorstores/mongodb_atlas)
