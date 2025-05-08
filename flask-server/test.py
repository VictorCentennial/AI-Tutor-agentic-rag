# from google.generativeai import configure, list_models
# import os
# from dotenv import load_dotenv
# load_dotenv()

# configure(api_key=os.getenv("GOOGLE_API_KEY"))

# available_models = list_models()
# print([model.name for model in available_models])
from typing import Dict
from utils.logging_config import setup_logging

logger = setup_logging()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask import send_from_directory
import tempfile


import logging
import re
import os
import json
from datetime import datetime, timedelta
import uuid
import shutil

from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import AIMessage, HumanMessage
from langgraph.types import Command

from dotenv import load_dotenv

print("before import rag")
from langchain.text_splitter import CharacterTextSplitter

print("before import GoogleGenerativeAIEmbeddings")

# from langchain_google_genai import GoogleGenerativeAIEmbeddings

print("import GoogleGenerativeAIEmbeddings")

from rag import rag

print("import splitter")
from rag.FAISS_vector_stores import (
    FAISSVectorStoreFactory,
)

print("import FAISSVectorStoreFactory")
from rag.MongoDB_vector_stores import MongoDBVectorStoreFactory

print("import MongoDBVectorStoreFactory")
from rag.Document_loader import (
    PDFDirectoryLoaderFactory,
    MultiDocumentDirectoryLoaderFactory,
)

print("import Document_loader")
from dotenv import load_dotenv

load_dotenv()
print("Hello, World!")
MONGODB_URI = os.getenv("MONGODB_URI")
print(MONGODB_URI)
