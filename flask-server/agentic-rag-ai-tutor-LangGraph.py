from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

import logging
import re
import os
import json
from datetime import datetime
import uuid

# from langchain.document_loaders import TextLoader
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import AIMessage, HumanMessage

from aiTutorAgent import aiTutorAgent

from rag import rag

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

thread_ids = []


# Function to load document content using LangChain
# def load_document_content(file_path):
#     try:
#         # Load documents from the file using TextLoader
#         loader = TextLoader(file_path)
#         documents = loader.load()

#         # Split text into smaller chunks
#         text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=1000, chunk_overlap=200
#         )
#         docs = text_splitter.split_documents(documents)

#         # Concatenate the chunks into a single context string
#         context = "\n".join([doc.page_content for doc in docs])
#         return context
#     except Exception as e:
#         return f"Error loading document content: {e}"


def get_graph_data(graph):
    # Convert the graph to a dictionary structure
    graph_data = {
        "nodes": {
            node_id: {"name": node.name, "metadata": node.metadata}
            for node_id, node in graph.nodes.items()
        },
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "data": edge.data,
                "conditional": edge.conditional,
            }
            for edge in graph.edges
        ],
    }
    return graph_data


def messages_to_json(messages):
    """
    Convert a list of LangChain messages to JSON format.

    Args:
        messages (list): A list of AIMessage and HumanMessage objects.

    Returns:
        str: A JSON string representing the list of messages.
    """
    messages_json = [
        (
            {"role": "ai", "content": message.content}
            if isinstance(message, AIMessage)
            else {"role": "student", "content": message.content}
        )
        for message in messages
    ]
    return messages_json  # json.dumps(messages_json)


def state_to_json(state_snapshot):
    """
    Parse the state snapshot to extract the necessary data and convert it to a JSON format.
    """

    def make_json_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_serializable(element) for element in obj]
        elif isinstance(obj, tuple):
            return [make_json_serializable(element) for element in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, AIMessage):
            return {"role": "ai", "content": obj.content}
        elif isinstance(obj, HumanMessage):
            return {"role": "human", "content": obj.content}
        elif hasattr(obj, "__dict__"):
            return make_json_serializable(vars(obj))
        elif obj is None:
            return None
        else:
            return obj

            # Use the recursive function to process the entire state snapshot

    state_json = make_json_serializable(state_snapshot)
    return state_json


@app.route("/get-folders", methods=["GET"])
def get_folders():
    try:
        course_material_path = "course_material"
        logging.debug(
            f"Looking for folders in: {os.path.abspath(course_material_path)}"
        )

        if not os.path.exists(course_material_path):
            logging.error(f"Directory not found: {course_material_path}")
            return jsonify({"error": "Course material directory not found"}), 404

        folders = [
            f
            for f in os.listdir(course_material_path)
            if os.path.isdir(os.path.join(course_material_path, f))
        ]

        logging.debug(f"Found folders: {folders}")
        return jsonify({"folders": folders})
    except Exception as e:
        logging.error(f"Error in get_folders: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/get-topics", methods=["GET"])
def get_topics():
    try:
        folder_name = request.args.get("folder")
        if not folder_name:
            return jsonify({"error": "No folder specified"}), 400

        folder_path = os.path.join("course_material", folder_name)
        if not os.path.exists(folder_path):
            return jsonify({"error": "Folder not found"}), 404

        # Get all files in the folder
        topics = [
            f
            for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]

        # Remove file extensions if desired
        topics = sorted([os.path.splitext(f)[0] for f in topics])

        return jsonify({"topics": topics})
    except Exception as e:
        logging.error(f"Error in get_topics: {str(e)}")
        return jsonify({"error": str(e)}), 500


def embed_documents(folder_path, vector_store_path):
    logging.debug(f"Loading documents from: {folder_path}")
    documents = rag.load_documents(folder_path)
    logging.debug(f"Documents loaded")

    logging.debug(f"Embedding documents")
    vector_store = rag.embed_documents()
    rag.save_vector_store(vector_store_path)
    logging.debug(f"Vector store created")


def load_vector_store(vector_store_path):
    logging.debug(f"Loading vector store from: {vector_store_path}")
    vector_store = rag.load_vector_store(vector_store_path)
    logging.debug(f"Vector store loaded")
    return vector_store


@app.route("/update-vector-store", methods=["POST"])
def update_vector_store():
    data = request.json
    folder_name = data.get("folder_name")
    folder_path = os.path.join("course_material", folder_name)
    vector_store_path = os.path.join("vector_store", folder_name)
    try:
        embed_documents(folder_path, vector_store_path)
        return jsonify({"message": f"Vector store for folder {folder_name} updated"})
    except Exception as e:
        logging.error(f"Error in update_vector_store: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/start-tutoring", methods=["POST"])
def start_tutoring():
    data = request.json
    # subject = data.get("subject", "Java")
    # topic = data.get("topic", "Polymorphism in Java")
    duration = data.get("duration", 30)
    folder_name = data.get("folder_name")  # Get the selected folder from request
    topic = data.get("topic")
    if not folder_name:
        return jsonify({"error": "No folder selected"}), 400

    folder_path = os.path.join("course_material", folder_name)
    vector_store_path = os.path.join("vector_store", folder_name)

    if not os.path.exists(folder_path):
        return jsonify({"error": "Selected folder not found"}), 404

    # print(f"topic: {topic}")
    # print(f"folder_name: {folder_name}")
    # print(f"vector_store_path: {vector_store_path}")
    # print(f"folder_path: {folder_path}")

    # check if vector store exists
    if not os.path.exists(vector_store_path):
        # through embedding
        embed_documents(folder_path, vector_store_path)
    # load from saved vector store
    vector_store = load_vector_store(vector_store_path)

    # logging.debug(f"Loading documents from: {folder_path}")
    # documents = rag.load_documents(folder_path)
    # logging.debug(f"Documents loaded")

    # logging.debug(f"Embedding documents")
    # vector_store = rag.embed_documents()

    # rag.save_vector_store(vector_store_path)

    # logging.debug(f"Vector store created: {vector_store}")
    if topic != "All topics":
        titles = rag.get_titles(topic)
    else:
        titles = rag.get_titles()

    # ##for loading from saved vector store
    # vector_store = rag.load_vector_store(vector_store_path)
    # titles = rag.get_titles()

    # Set vector store on aiTutorAgent instance
    aiTutorAgent.vector_store = vector_store

    # # Clear the conversation memory at the start of a new session
    # aiTutorAgent.memory.chat_memory.clear()

    # Load context content from the document
    # context = load_document_content(file_path)

    initial_input = {
        "subject": folder_name,
        # "topic": topic,
        "titles": titles,
        "summary": "",
        "messages": [],
        "answer_trials": 0,
        "start_time": datetime.now(),
        "duration_minutes": duration,
        "tutor_question": "",
    }

    thread_id = str(uuid.uuid4())
    thread_ids.append(thread_id)
    thread = {"configurable": {"thread_id": str(thread_id)}}

    response = aiTutorAgent.graph.invoke(initial_input, thread)
    response_json = messages_to_json(response["messages"])
    state = aiTutorAgent.graph.get_state(thread)
    next_state = state.next[0] if state.next else ""

    # print(f"State: {state_to_json(state)}")
    # print(f"jsonify: {jsonify( {"state": state_to_json(state)})}")

    return jsonify(
        {
            "messages": response_json,
            "thread_id": thread_id,
            "state": state_to_json(state),
            "next_state": next_state,
        }
    )


# API endpoint to handle student responses and continue the session
@app.route("/continue-tutoring", methods=["POST"])
def continue_tutoring():
    data = request.json
    student_response = data.get("student_response", "")
    thread_id = data.get("thread_id")
    thread = {"configurable": {"thread_id": str(thread_id)}}

    aiTutorAgent.graph.update_state(
        thread, {"messages": [HumanMessage(content=student_response)]}
    )

    response = aiTutorAgent.graph.invoke(None, thread)
    response_json = messages_to_json(response["messages"])
    state = aiTutorAgent.graph.get_state(thread)
    next_state = state.next[0] if state.next else ""

    # print(f"State: {state_to_json(state)}")
    # logging.info(f"jsonify: {jsonify( {"state": state_to_json(state)})}")
    # logging.info(f"next_state: {next_state}")
    return jsonify(
        {
            "messages": response_json,
            "thread_id": thread_id,
            "state": state_to_json(state),
            "next_state": next_state,
        }
    )


@app.route("/save-session", methods=["POST"])
def save_session_history():
    SESSION_HISTORY_DIR = "saved_session_history"
    if not os.path.exists(SESSION_HISTORY_DIR):
        os.makedirs(SESSION_HISTORY_DIR)

    try:
        data = request.json
        thread_id = data.get("thread_id")
        thread = {"configurable": {"thread_id": str(thread_id)}}
        state = aiTutorAgent.graph.get_state(thread)
        message_history = state.values["messages"]
        subject = state.values["subject"]
        start_time = state.values["start_time"]
        end_time = datetime.now()

        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{thread_id}.txt"
        filepath = os.path.join(SESSION_HISTORY_DIR, filename)

        with open(filepath, "w") as file:
            file.write(f"Subject: {subject}\n")
            file.write(f"Start Time: {start_time}\n")
            file.write(f"End Time: {end_time}\n")
            file.write("-" * 80 + "\n")

            for message in message_history:
                role = (
                    "AI Message" if isinstance(message, AIMessage) else "Human Message"
                )
                header = f" {role} "
                separator = "=" * ((80 - len(header)) // 2)
                file.write(f"{separator}{header}{separator}\n")
                file.write(f"{message.content}\n\n")

        # Return session summary data in response
        summary = {
            "subject": subject,
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "messages": [
                {"role": "AI" if isinstance(msg, AIMessage) else "Human", "content": msg.content}
                for msg in message_history
            ],
        }
        return jsonify({"message": f"Session history saved to {filepath}", "summary": summary})

    except Exception as e:
        logging.error(f"Error in save_session_history: {str(e)}")
        return jsonify({"error": "Failed to save session", "details": str(e)}), 500

@app.route("/download-session", methods=["POST"])
def download_session_history():
    SESSION_HISTORY_DIR = "saved_session_history"
    try:
        data = request.json
        thread_id = data.get("thread_id")
        filename = f"session_{thread_id}.txt"
        # Use the latest file (if multiple matches)
        file_path = os.path.join(SESSION_HISTORY_DIR, filename )

        return send_file(
            file_path,
            mimetype="text/plain",
            as_attachment=True,
            download_name=os.path.basename(file_path)
        )
    except Exception as e:
        logging.error(f"Error in download_session_history: {str(e)}")
        return jsonify({"error": "Failed to download session history", "details": str(e)}), 500


@app.route("/get-graph", methods=["GET"])
def get_graph_image():
    graph = aiTutorAgent.graph.get_graph()
    graph_data = get_graph_data(graph)
    return jsonify({"graph": graph_data})


# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
