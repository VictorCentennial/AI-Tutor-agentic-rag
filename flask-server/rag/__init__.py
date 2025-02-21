from langchain.text_splitter import CharacterTextSplitter
from rag.FAISS_vector_stores import (
    FAISSVectorStoreFactory,
    PDFDirectoryLoaderFactory,
    MultiDocumentDirectoryLoaderFactory,
)

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
from rag.RAG import RAG

load_dotenv()

# Initialize dependencies
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
vector_store_factory = FAISSVectorStoreFactory()
# document_loader_factory = PDFDirectoryLoaderFactory()
document_loader_factory = MultiDocumentDirectoryLoaderFactory()

# Create RAG instance
rag = RAG(
    embeddings=embeddings,
    text_splitter=text_splitter,
    document_loader_factory=document_loader_factory,
    vector_store_factory=vector_store_factory,
)
