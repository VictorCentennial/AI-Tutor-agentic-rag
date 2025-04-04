# AI Tutor with RAG and LangGraph

An intelligent tutoring system that uses Retrieval-Augmented Generation (RAG) and LangGraph for adaptive learning experiences.

## Setup Instructions

### Environment Parameters Setup

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

## Azure Deployment Guide

Follow these steps to deploy the application to Azure Container Instances (ACI):

### 1. Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed on your machine
- Docker installed on your machine
- Active Azure account with a subscription

### 2. Set Up Azure Resources

1. **Login to Azure**:

   ```bash
   az login
   ```

2. **Create a Resource Group** (if not already created):

   ```bash
   az group create --name ai_tutor --location eastus
   ```

3. **Create an Azure Container Registry (ACR)**:

   ```bash
   az acr create --resource-group ai_tutor --name aitutoracr --sku Basic --admin-enabled true
   ```

4. **Get ACR credentials**:

   ```bash
   az acr credential show --name aitutoracr
   ```

   Note down the username and password for later use.

### 3. Build and Push Docker Images

1. **Login to ACR**:

   ```bash
   az acr login --name aitutoracr
   ```

2. **Build and tag the Flask server image**:

   ```bash
   cd path/to/project
   docker build -t aitutoracr.azurecr.io/flask-server:latest ./flask-server
   ```

3. **Build and tag the React client image**:

   ```bash
   docker build -t aitutoracr.azurecr.io/react-client:latest ./react-client
   ```

4. **Push the images to ACR**:

   ```bash
   docker push aitutoracr.azurecr.io/flask-server:latest
   docker push aitutoracr.azurecr.io/react-client:latest
   ```

### 4. Create a Container Group YAML File

Create a file named `container-group.yaml` with the content follow the `container-group-template.yaml`

### 5. Deploy the Container Group

Deploy the container group using the YAML file:

```bash
az container create --resource-group ai_tutor --file container-group.yaml
```

### 6. Check Deployment Status

1. **Check container group status**:

   ```bash
   az container show --resource-group ai_tutor --name ai-tutor-containers
   ```

2. **View container logs**:

   ```bash
   az container logs --resource-group ai_tutor --name ai-tutor-containers --container-name flask-server
   az container logs --resource-group ai_tutor --name ai-tutor-containers --container-name react-client
   ```

### 7. Access Your Application

Once deployed, your application will be accessible at:

- **Frontend**: `http://ai-tutor-app.eastus.azurecontainer.io`
- **Backend API**: `http://ai-tutor-app.eastus.azurecontainer.io:5001`

### Troubleshooting

If you encounter issues with container startup:

1. **Create a debug container** to check environment variables and configurations:

   ```yaml
   # debug-container.yaml
   apiVersion: 2019-12-01
   location: eastus
   name: ai-tutor-debug
   properties:
     containers:
     - name: flask-server
       properties:
         image: aitutoracr.azurecr.io/flask-server:latest
         command: ["/bin/bash", "-c", "cd /app && ls -la && pip list && python -V && python agentic-rag-ai-tutor-LangGraph.py 2>&1"]
         # Rest of the configuration similar to your main container group
   ```

2. **Deploy and check logs** of the debug container:

   ```bash
   az container create --resource-group ai_tutor --file debug-container.yaml
   az container logs --resource-group ai_tutor --name ai-tutor-debug --container-name flask-server
   ```

3. **Check MongoDB connectivity** from within the container.
