FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and filter script
COPY requirements.txt filter_requirements.py ./

# Create Docker-specific requirements file
RUN python filter_requirements.py && \
    pip install --no-cache-dir -r requirements-docker.txt

COPY . .

# Expose the port your Flask app runs on 
EXPOSE 5001

CMD ["python", "agentic-rag-ai-tutor-LangGraph.py"]