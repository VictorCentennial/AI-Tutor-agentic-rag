# AI Tutor with RAG and LangGraph

An intelligent tutoring system that uses Retrieval-Augmented Generation (RAG) and LangGraph for adaptive learning experiences.

## Setup Instructions

### Environment Parameters Setup:

1. Create a `.env` file in the `flask-server` directory can follow the `.env.template` file.
2. Provide API key and models

### Backend Setup (Flask Server)
1. Create and activate a virtual environment:
```
cd flask-server
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Run the Flask server:
```
python agentic-rag-ai-tutor-LangGraph.py
```

### Frontend Setup (React Client)

1. Install dependencies:
```
cd react-client
npm install
```

2. Run the React client:
```
npm run dev
```

P.S. To show the debug mode, you can add `.env` file in the `react-client` directory and set `VITE_DEBUG_MODE=true`.
