from flask import Flask, request, jsonify
from flask_cors import CORS

import logging
import re
import os
import json
from datetime import datetime

# from langchain.document_loaders import TextLoader
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import AIMessage, HumanMessage

from aiTutorAgent import aiTutorAgent

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# TODO: Use UUID for thread ID, and list of active threads
thread_id = 0
# TODO:create unique id for each thread
thread = {"configurable": {"thread_id": str(thread_id)}}


# Function to load document content using LangChain
def load_document_content(file_path):
    try:
        # Load documents from the file using TextLoader
        loader = TextLoader(file_path)
        documents = loader.load()

        # Split text into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        docs = text_splitter.split_documents(documents)

        # Concatenate the chunks into a single context string
        context = "\n".join([doc.page_content for doc in docs])
        return context
    except Exception as e:
        return f"Error loading document content: {e}"


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


@app.route("/start-tutoring", methods=["POST"])
def start_tutoring():
    data = request.json
    subject = data.get("subject", "Java")
    topic = data.get("topic", "Polymorphism in Java")
    file_name = data.get("file_name", "topic_material.txt")
    file_path = os.path.join("data", file_name)

    # # Clear the conversation memory at the start of a new session
    # aiTutorAgent.memory.chat_memory.clear()

    # Load context content from the document
    context = load_document_content(file_path)

    initial_input = {
        "subject": subject,
        "topic": topic,
        "context": context,
        "summary": "",
        "messages": [],
        "answer_trials": 0,
        "start_time": datetime.now(),
        "duration_minutes": 30,
    }

    response = aiTutorAgent.graph.invoke(initial_input, thread)
    response_json = messages_to_json(response["messages"])
    state = aiTutorAgent.graph.get_state(thread)

    return jsonify(
        {"messages": response_json, "thread_id": thread_id}
    )  # , "state": state})


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

    return jsonify(
        {"messages": response_json, "thread_id": thread_id}
    )  # , "state": state})


# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
