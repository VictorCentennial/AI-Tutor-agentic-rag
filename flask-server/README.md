# AI Tutor Agentic RAG Server

This repository contains a Flask server for an AI Tutor system using agentic retrieval-augmented generation (RAG).

## Installation and Setup Using UV

[UV](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. Here's how to set up and run this project using UV.

### 1. Install UV

First, install UV on your system:

#### Windows

```bash
pip install uv
```

#### macOS/Linux

```bash
curl -sSf https://astral.sh/uv/install.sh | bash
```

### 2. Create a Virtual Environment

Navigate to the project directory and create a new virtual environment:

```bash
cd path/to/flask-server
uv venv
```

### 3. Activate the Virtual Environment

#### Windows

```bash
.venv\Scripts\activate
```

#### macOS/Linux

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

UV can install dependencies from the project files directly:

```bash
uv pip install -e .
```

Alternatively, if you prefer using a requirements file:

```bash
# Generate requirements.txt from imports
uv pip compile agentic-rag-ai-tutor-LangGraph.py -o requirements.txt

# Install from requirements.txt
uv pip install -r requirements.txt
```

### 5. Environment Variables

Create a `.env` file in the project root by copying the provided `.env.template` file:

```bash
cp .env.template .env
```

Then, edit the `.env` file and fill in the following required variables:

```
GOOGLE_API_KEY=your_google_api_key
GOOGLE_MODEL_NAME=gemini-2.0-flash
OPENAI_API_KEY=your_openai_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_PROJECT="ai-tutor-rag"

MONGODB_URI=your_mongodb_connection_string
databaseName=ai_tutor_rag
collectionName=ai_agent_checkpoints

FLASK_HOST=0.0.0.0
FLASK_PORT=5001
FLASK_DEBUG=True
```

Replace the placeholder values with your actual API keys and connection strings.

### 6. Run the Server

Start the Flask server:

```bash
python agentic-rag-ai-tutor-LangGraph.py
```

The server will be available at `http://localhost:5001`.

## Project Structure

- `agentic-rag-ai-tutor-LangGraph.py`: Main Flask server application
- `aiTutorAgent.py`: AI Tutor agent implementation
- `rag.py`: Retrieval-augmented generation module

## API Endpoints

- `/get-folders`: Get available course folders
- `/get-topics`: Get course topics for a specified folder and week
- `/update-vector-store`: Update vector store for a folder
- `/start-tutoring`: Start a tutoring session
- `/continue-tutoring`: Continue an existing tutoring session
- `/save-session`: Save the current session history
- `/download-session`: Download a saved session history

## Troubleshooting

- **Character Encoding Errors**: The application uses UTF-8 encoding to handle special characters in saved files.
- **Vector Store Issues**: If you encounter vector store errors, try updating the vector store using the provided endpoint.
