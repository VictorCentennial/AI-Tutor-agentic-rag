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
from aiTutorAgent import aiTutorAgent, chat_history_mongodb
from rag import rag

from dotenv import load_dotenv

import threading
import time

from uuid import uuid4

from config import TOTAL_WEEKS

load_dotenv()


use_mongodb = os.environ.get("USE_MONGODB", "true").lower() == "true"


MONGODB_DB = os.getenv("MONGODB_DB", "ai_tutor_db")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "agent_checkpoints")


SESSION_HISTORY_DIR = "saved_session_history"
COURSE_MATERIAL_DIR = "course_material"


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

thread_ids = []

# to store local vector stores and their access times
app.vector_stores = {}
app.vector_store_access_times = {}


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
        if use_mongodb:
            folders = rag.get_courses()
            logging.debug(f"Found folders: {folders}")
            return jsonify({"folders": folders})
        else:
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
        course_name = request.args.get("folder")
        logging.debug(f"Course name: {course_name}")
        if use_mongodb:
            topics: Dict[int, str] = rag.get_topics(course_name)
            topics_list = []
            for week in range(1, TOTAL_WEEKS + 1):
                if week in topics:
                    topics_list.append(f"{week}: {topics[week]}")
                else:
                    topics_list.append(f"{week}")
            logging.debug(f"Found topics: {topics_list}")
            return jsonify({"topics": topics_list})
        else:
            folder_name = request.args.get("folder")
            current_week = request.args.get("current_week")
            if not folder_name:
                return jsonify({"error": "No folder specified"}), 400

            if not current_week:
                return jsonify({"error": "No current week specified"}), 400

            try:
                current_week = int(current_week)
            except ValueError:
                return jsonify({"error": "Invalid current week value"}), 400

            folder_path = os.path.join("course_material", folder_name)
            if not os.path.exists(folder_path):
                return jsonify({"error": "Folder not found"}), 404

            # Get all files in the folder
            topics_uptil_current_week = []
            for week in range(1, current_week + 1):
                week_path = os.path.join(folder_path, str(week))
                week_topics = os.listdir(week_path)
                topics_with_path = [rf"{week}\{topic}" for topic in week_topics]
                topics_uptil_current_week.extend(topics_with_path)

            topics_uptil_current_week = sorted(
                [os.path.splitext(f)[0] for f in topics_uptil_current_week]
            )

            return jsonify({"topics": topics_uptil_current_week})
    except Exception as e:
        logging.error(f"Error in get_topics: {str(e)}")
        return jsonify({"error": str(e)}), 500


def embed_documents(folder_path, vector_store_path):
    logging.debug(f"Loading documents from: {folder_path}")
    documents = rag.load_documents(folder_path)

    # Clean and normalize the text before embedding
    for doc in documents:
        # Remove extra spaces between characters
        doc.page_content = " ".join(doc.page_content.split())

    logging.debug(f"Documents loaded")

    logging.debug(f"Embedding documents")
    vector_store = rag.embed_documents()
    rag.save_vector_store(vector_store_path)
    logging.debug(f"Vector store created")


def embed_documents_mongodb(folder_name, folder_path, week):
    rag.load_from_folder_path_to_mongodb_vector_store(folder_name, week, folder_path)

    # metadata = {
    #     "course": folder_name,
    #     "week": week,
    # }
    # logging.info(f"Embedding documents for course{folder_name}, week{week}")

    # # TODO store UUID for each document for fast delection
    # documents = rag.load_documents(folder_path, metadata=metadata)
    # aiTutorAgent.vector_store.add_documents(documents=documents)


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

    if use_mongodb:
        vector_store = aiTutorAgent.vector_store
        # delete all documents for the course
        rag.delete_by_course(folder_name)
    else:
        # create vector store folder if it doesn't exist
        if not os.path.exists(vector_store_path):
            os.makedirs(vector_store_path)

    try:
        for week in range(1, TOTAL_WEEKS + 1):
            # create folder for each week if it doesn't exist
            folder_path_week = os.path.join(folder_path, str(week))
            if not os.path.exists(folder_path_week):
                os.makedirs(folder_path_week)
                continue
            # create vector store for each week if it doesn't exist
            vector_store_path_week = os.path.join(vector_store_path, str(week))
            if not os.path.exists(vector_store_path_week):
                os.makedirs(vector_store_path_week)
            # if the folder is empty, ignore that week
            if not os.listdir(folder_path_week):
                continue
            # remove existing files inside vector store if it exists
            if os.path.exists(vector_store_path_week):
                for file in os.listdir(vector_store_path_week):
                    os.remove(os.path.join(vector_store_path_week, file))
            # embed documents for each week
            if use_mongodb:
                embed_documents_mongodb(folder_name, folder_path_week, week)
            else:
                embed_documents(folder_path_week, vector_store_path_week)
            logging.info(f"Course {folder_name} Week {week} vector store created")

        return jsonify({"message": f"Vector store for folder {folder_name} updated"})
    except Exception as e:
        logging.error(f"Error in update_vector_store: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/start-tutoring", methods=["POST"])
def start_tutoring():
    data = request.json
    duration = data.get("duration", 30)
    folder_name = data.get("folder_name")  # Get the selected folder from request
    topic = data.get("topic")
    current_week = data.get("current_week")
    student_id = data.get("student_id")

    logger.info(
        f"Starting tutoring for {folder_name} with topic {topic} and current week {current_week}"
    )

    if not folder_name:
        return jsonify({"error": "No folder selected"}), 400

    vector_store_paths = []

    thread_id = str(uuid.uuid4())

    if not use_mongodb:
        vector_store = None

        folder_path = os.path.join("course_material", folder_name)

        if not os.path.exists(folder_path):
            return jsonify({"error": "Selected folder not found"}), 404

        for week in range(1, int(current_week) + 1):
            logging.info(f"Processing week {week}")
            vector_store_path_week = os.path.join(
                "vector_store", folder_name, str(week)
            )
            folder_path_week = os.path.join("course_material", folder_name, str(week))
            if not os.path.exists(folder_path_week):
                logging.error(f"Week {week} Folder not found: {folder_path_week}")
                # create empty folder
                os.makedirs(folder_path_week)
                continue
            # if the folder is empty, ignore that week
            if not os.listdir(folder_path_week):
                logging.info(f"Week {week} Folder is empty: {folder_path_week}")
                continue
            # check if the vector store exists, if not, embed the documents and create it
            if not os.path.exists(vector_store_path_week):
                embed_documents(folder_path_week, vector_store_path_week)
                logging.info(
                    f"Vector store created for week {week}: {vector_store_path_week}"
                )
            vector_store_paths.append(vector_store_path_week)

        # merge all vector stores
        if len(vector_store_paths) > 0:
            logging.info(f"Merging vector stores for folder {folder_name}")
            logging.info(f"Vector store paths: {vector_store_paths}")
            vector_store = load_vector_store(vector_store_paths)
        else:
            logging.error(f"No vector stores found for folder {folder_name}")
            return jsonify({"error": "No vector stores found for folder"}), 404

        app.vector_stores[thread_id] = vector_store
        update_vector_store_access_time(thread_id)  # Track access time

    thread_ids.append(thread_id)

    weeks_selected_list = []

    print(f"current_week: {current_week}")

    if topic != "ALL":
        week_selected = topic.split("\\", 2)[0]
        weeks_selected_list.append(int(week_selected))
        if len(topic.split("\\", 2)) == 2:
            topic = topic.split("\\", 2)[1]
        else:
            topic = None
    else:
        topic = None
        weeks_selected_list = [week for week in range(1, int(current_week) + 1)]

    if use_mongodb:
        titles = rag.get_titles_Mongodb(folder_name, weeks_selected_list)
        logging.info(f"Week Selected: {weeks_selected_list}")

        # if no titles are found, consider all weeks
        if len(titles) == 0:
            weeks_selected_list = [week for week in range(1, int(current_week) + 1)]
            titles = rag.get_titles_Mongodb(folder_name, weeks_selected_list)
    else:
        titles = rag.get_titles(topic)
        logging.info(f"Topic Selected: {topic}")

    initial_input = {
        "subject": folder_name,
        "topic": topic,
        "week_selected": weeks_selected_list,
        "titles": titles,
        "summary": "",
        "messages": [],
        "answer_trials": 0,
        "start_time": datetime.now(),
        "duration_minutes": duration,
        "tutor_question": "",
        "student_question": "",
        "task_breakdown": [],
        "current_task_index": 0,
        "task_solving_start_index": 0,
        "vector_store_paths": vector_store_paths,  # Store vector store paths in the state
        "current_week": current_week,  # Store current week for recovery purposes
        "use_mongodb_vector_store": use_mongodb,
    }

    thread = {"configurable": {"thread_id": str(thread_id), "user_id": str(student_id)}}

    response = aiTutorAgent.graph.invoke(initial_input, thread)
    response_json = messages_to_json(response["messages"])
    state = aiTutorAgent.graph.get_state(thread)
    next_state = state.next[0] if state.next else ""

    # print(f"State: {state_to_json(state)}")
    # print(f"jsonify: {jsonify( {"state": state_to_json(state)})}")

    graph = aiTutorAgent.graph.get_graph()
    # save the graph
    # create graph folder if it doesn't exist
    graph_folder = "graph"
    if not os.path.exists(graph_folder):
        os.makedirs(graph_folder)
    try:
        graph.draw_mermaid_png(output_file_path=os.path.join(graph_folder, "graph.png"))
    except Exception as e:
        logging.error(f"Error in draw_mermaid_png: {str(e)}")

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
    student_id = data.get("student_id")
    thread = {"configurable": {"thread_id": str(thread_id), "user_id": str(student_id)}}

    if not use_mongodb:
        # Update access time if this thread has a vector store
        if thread_id in app.vector_stores:
            update_vector_store_access_time(thread_id)

        else:
            # Recovery mechanism - try to recreate the vector store
            try:
                logging.info(
                    f"Vector store missing for thread {thread_id}. Attempting recovery..."
                )

                # Get the session state
                state = aiTutorAgent.graph.get_state(thread)

                # Extract vector_store_paths and other necessary information from state
                vector_store_paths = state.values.get("vector_store_paths", [])
                folder_name = state.values.get("subject")
                current_week = state.values.get("current_week")

                logging.info(
                    f"Recovery details: folder={folder_name}, current_week={current_week}, paths={vector_store_paths}"
                )

                if vector_store_paths:
                    # Recreate the vector store from the saved paths
                    vector_store = load_vector_store(vector_store_paths)
                    app.vector_stores[thread_id] = vector_store
                    update_vector_store_access_time(thread_id)
                    logging.info(
                        f"Successfully recovered vector store for thread {thread_id}"
                    )
                elif folder_name and current_week:
                    # If paths not available but we have folder name and week, try to rebuild paths
                    logging.info(
                        f"No vector store paths available. Rebuilding from folder and week..."
                    )
                    rebuilt_vector_store_paths = []

                    for week in range(1, int(current_week) + 1):
                        vector_store_path_week = os.path.join(
                            "vector_store", folder_name, str(week)
                        )
                        if os.path.exists(vector_store_path_week):
                            rebuilt_vector_store_paths.append(vector_store_path_week)

                    if rebuilt_vector_store_paths:
                        vector_store = load_vector_store(rebuilt_vector_store_paths)
                        app.vector_stores[thread_id] = vector_store
                        update_vector_store_access_time(thread_id)

                        # Update the state with the rebuilt paths
                        aiTutorAgent.graph.update_state(
                            thread, {"vector_store_paths": rebuilt_vector_store_paths}
                        )
                        logging.info(
                            f"Successfully rebuilt vector store for thread {thread_id}"
                        )
                    else:
                        logging.error(
                            f"Could not find any vector store paths for recovery"
                        )
                else:
                    logging.error(f"Insufficient information for vector store recovery")
            except Exception as e:
                logging.error(f"Vector store recovery failed: {str(e)}")

    try:
        response = aiTutorAgent.graph.invoke(Command(resume=student_response), thread)

        response_json = messages_to_json(response["messages"])
        state = aiTutorAgent.graph.get_state(thread)
        next_state = state.next[0] if state.next else ""

        return jsonify(
            {
                "messages": response_json,
                "thread_id": thread_id,
                "state": state_to_json(state),
                "next_state": next_state,
            }
        )
    except Exception as e:
        logging.error(f"Error in continue_tutoring: {str(e)}")
        return (
            jsonify(
                {"error": "Failed to continue tutoring session", "details": str(e)}
            ),
            500,
        )


@app.route("/save-session", methods=["POST"])
def save_session_history():
    if not os.path.exists(SESSION_HISTORY_DIR):
        os.makedirs(SESSION_HISTORY_DIR)

    try:
        data = request.json
        thread_id = data.get("thread_id")
        student_id = data.get("student_id")
        topic_code = data.get("topic_code")  # Updated field name
        time_stamp = data.get("time_stamp")
        thread = {
            "configurable": {"thread_id": str(thread_id), "user_id": str(student_id)}
        }
        state = aiTutorAgent.graph.get_state(thread)
        message_history = state.values["messages"]
        subject = state.values["subject"]
        start_time = state.values["start_time"]
        end_time = datetime.now()
        logging.info(f"mesage history: {message_history}")
        # Debugging: Log the received data
        logging.info(f"Received data: {data}")
        logging.info(f"Topic Code: {topic_code}")
        logging.info(f"Date Time: {time_stamp}")

        # Create a filename using the provided date_time and topic_code
        filename = f"{time_stamp}_{topic_code}_{student_id}.txt"
        filepath = os.path.join(SESSION_HISTORY_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as file:
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
                {
                    "role": "AI" if isinstance(msg, AIMessage) else "Human",
                    "content": msg.content,
                }
                for msg in message_history
            ],
        }
        return jsonify(
            {"message": f"Session history saved to {filepath}", "summary": summary}
        )

    except Exception as e:
        logging.error(f"Error in save_session_history: {str(e)}")
        return jsonify({"error": "Failed to save session", "details": str(e)}), 500


@app.route("/download-session", methods=["POST"])
def download_session_history():
    try:
        data = request.json
        thread_id = data.get("thread_id")
        student_id = data.get("student_id")
        topic_code = data.get("topic_code")  # Updated field name
        time_stamp = data.get("time_stamp")  # New field for date and time
        filename = f"{time_stamp}_{topic_code}_{student_id}.txt"

        logging.info(f"student id: {student_id}")
        logging.info(f"topic code: {topic_code}")
        logging.info(f"time stamp: {time_stamp}")
        logging.info(f"downloading session history: {filename}")
        # Use the latest file (if multiple matches)
        file_path = os.path.join(SESSION_HISTORY_DIR, filename)

        return send_file(
            file_path,
            mimetype="text/plain",
            as_attachment=True,
            download_name=os.path.basename(file_path),
        )
    except Exception as e:
        logging.error(f"Error in download_session_history: {str(e)}")
        return (
            jsonify({"error": "Failed to download session history", "details": str(e)}),
            500,
        )


@app.route("/get-graph", methods=["GET"])
def get_graph_image():
    graph = aiTutorAgent.graph.get_graph()
    graph_data = get_graph_data(graph)
    return jsonify({"graph": graph_data})


@app.route("/update-duration", methods=["PUT"])
def update_duration():
    data = request.json
    duration_minutes = data.get("duration_minutes")
    thread_id = data.get("thread_id")
    print(f"duration_minutes: {duration_minutes}")
    print(f"thread_id: {thread_id}")
    try:
        aiTutorAgent.extend_duration(str(thread_id), int(duration_minutes))
        return jsonify({"message": "Duration updated successfully"})
    except Exception as e:
        logging.error(f"Error in update_duration: {str(e)}")
        return jsonify({"error": "Failed to update duration", "details": str(e)}), 500


@app.route("/get-sessions", methods=["POST"])
def get_sessions():
    try:
        data = request.json
        student_id = data.get("student_id")
        date = data.get("date")
        course_code = data.get("course_code")

        sessions = []

        for filename in os.listdir(SESSION_HISTORY_DIR):
            if filename.endswith(".txt"):
                # Use regex to extract parts of the filename
                match = re.match(r"(\d{8})_(\d{4})_(.+)_(.+)\.txt", filename)
                if match:
                    file_date, file_time, file_course, file_student_id = match.groups()

                    # Apply filters (only check fields that are provided)
                    matches_student_id = not student_id or file_student_id == student_id
                    matches_date = not date or file_date == date
                    matches_course_code = not course_code or file_course == course_code

                    if matches_student_id and matches_date and matches_course_code:
                        sessions.append(
                            {
                                "filename": filename,
                                "student_id": file_student_id,
                                "course_code": file_course,
                                "date": file_date,
                                "time": file_time,
                                "filepath": os.path.join(SESSION_HISTORY_DIR, filename),
                            }
                        )

        return jsonify({"sessions": sessions})

    except Exception as e:
        logging.error(f"Error in get_sessions: {str(e)}")
        return jsonify({"error": "Failed to fetch sessions", "details": str(e)}), 500


@app.route("/general-analysis", methods=["POST"])
def general_analysis():
    try:

        conversations = chat_history_mongodb.get_chat_history_all()
        combined_content = _combine_conversation_messages(conversations)
        session_data = chat_history_mongodb.get_all_session_data()
        logging.info(f"combined_content for general analysis: {combined_content}")

        # session_files = _get_all_session_files()
        # combined_content = _combine_session_files(session_files)
        # session_data = _get_session_data()
        analysis_result = aiTutorAgent.general_analysis(combined_content, session_data)
        return jsonify(analysis_result)

    except Exception as e:
        logging.error(f"Error in general_analysis: {str(e)}")
        return (
            jsonify({"error": "Failed to perform general analysis", "details": str(e)}),
            500,
        )


@app.route("/student-analysis", methods=["POST"])
def student_analysis():
    try:
        data = request.json
        student_id = data.get("student_id")

        if not student_id:
            return jsonify({"error": "Student ID is required"}), 400

        conversations = chat_history_mongodb.get_chat_history_by_student_id(student_id)
        session_data = chat_history_mongodb.get_all_session_data()
        logging.info(f"conversations for student analysis: {conversations}")
        combined_content = _combine_conversation_messages(conversations)
        logging.info(f"combined_content for student analysis: {combined_content}")
        # session_files = _get_session_files_by_student(student_id)
        # combined_content = _combine_session_files(session_files)

        analysis_result = aiTutorAgent.student_analysis(
            student_id, combined_content, session_data
        )
        return jsonify(analysis_result)
    except Exception as e:
        logging.error(f"Error in student_analysis: {str(e)}")
        return (
            jsonify({"error": "Failed to perform student analysis", "details": str(e)}),
            500,
        )


@app.route("/course-analysis", methods=["POST"])
def course_analysis():
    try:
        data = request.json
        course_code = data.get("course_code")

        if not course_code:
            return jsonify({"error": "Course Code is required"}), 400

        conversations = chat_history_mongodb.get_chat_history_by_course_code(
            course_code
        )
        session_data = chat_history_mongodb.get_all_session_data()
        combined_content = _combine_conversation_messages(conversations)
        logging.info(f"combined_content for course analysis: {combined_content}")
        # else:
        #     session_files = _get_session_files_by_course(course_code)
        #     combined_content = _combine_session_files(session_files)
        #     session_data = _get_session_data()
        analysis_result = aiTutorAgent.course_analysis(
            course_code, combined_content, session_data
        )
        return jsonify(analysis_result)
    except Exception as e:
        logging.error(f"Error in course_analysis: {str(e)}")
        return (
            jsonify({"error": "Failed to perform course analysis", "details": str(e)}),
            500,
        )


@app.route("/day-analysis", methods=["POST"])
def day_analysis():
    try:
        data = request.json
        date = data.get("date")

        if not date:
            return jsonify({"error": "Date is required"}), 400

        conversations = chat_history_mongodb.get_chat_history_by_date(date)
        combined_content = _combine_conversation_messages(conversations)
        session_data = chat_history_mongodb.get_all_session_data()
        logging.info(f"combined_content for day analysis: {combined_content}")
        # else:
        #     session_files = _get_session_files_by_date(date)
        #     combined_content = _combine_session_files(session_files)
        #     session_data = _get_session_data()
        analysis_result = aiTutorAgent.day_analysis(
            date, combined_content, session_data
        )
        return jsonify(analysis_result)
    except Exception as e:
        logging.error(f"Error in day_analysis: {str(e)}")
        return (
            jsonify({"error": "Failed to perform day analysis", "details": str(e)}),
            500,
        )


@app.route("/get-all-students-id", methods=["GET"])
def get_all_students_id():
    return jsonify(chat_history_mongodb.get_all_student_ids())


@app.route("/statistics", methods=["GET"])
def get_statistics():
    try:
        total_sessions = 0
        total_students = 0
        total_courses = 0

        if use_mongodb:
            # Get total number of sessions from MongoDB
            total_sessions = len(chat_history_mongodb.get_all_threads())
            total_students = len(chat_history_mongodb.get_all_student_ids())
            total_courses = len(rag.get_courses_from_structure())
        else:
            # Check if directories exist
            if not os.path.exists(SESSION_HISTORY_DIR):
                return (
                    jsonify({"error": f"Directory not found: {SESSION_HISTORY_DIR}"}),
                    500,
                )
            if not os.path.exists(COURSE_MATERIAL_DIR):
                return (
                    jsonify({"error": f"Directory not found: {COURSE_MATERIAL_DIR}"}),
                    500,
                )

            # Count total number of sessions
            session_files = [
                name
                for name in os.listdir(SESSION_HISTORY_DIR)
                if name.endswith(".txt")
            ]
            total_sessions = len(session_files)

            # Count total number of unique students (safe extraction)
            student_ids = set()
            for filename in session_files:
                parts = filename.split("_")
                if (
                    len(parts) > 3
                ):  # Ensure there are enough parts before accessing index 3
                    student_id = parts[3].split(".")[0]  # Extract student ID
                    student_ids.add(student_id)

            total_students = len(student_ids)

            # Count total number of courses
            course_dirs = [
                name
                for name in os.listdir(COURSE_MATERIAL_DIR)
                if os.path.isdir(os.path.join(COURSE_MATERIAL_DIR, name))
            ]
            total_courses = len(course_dirs)

        return jsonify(
            {
                "total_sessions": total_sessions,
                "total_students": total_students,
                "total_courses": total_courses,
            }
        )

    except Exception as e:
        logging.error(f"Error in get_statistics: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to fetch statistics", "details": str(e)}), 500


# Route to get the list of courses
@app.route("/get-courses", methods=["GET"])
def get_courses():
    try:
        if use_mongodb:
            courses = rag.get_courses_from_structure()
            return jsonify({"courses": courses})
        else:
            course_material_path = "course_material"
            if not os.path.exists(course_material_path):
                return jsonify({"error": "Course material directory not found"}), 404

            # Get all folders (courses) in the course_material directory
            courses = [
                f
                for f in os.listdir(course_material_path)
                if os.path.isdir(os.path.join(course_material_path, f))
            ]
            return jsonify({"courses": courses})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to get the material for a specific course
@app.route("/get-course-material", methods=["GET"])
def get_course_material():
    try:
        if use_mongodb:
            course_name = request.args.get("course")
            if not course_name:
                return jsonify({"error": "No course specified"}), 400
            material_from_structure = rag.get_course_material_from_structure(
                course_name
            )
            material = {}
            for week, info in material_from_structure.items():
                # info is the dict for that week
                file_list = info.get("files", [])  # safely get the list (or empty list)
                material[week] = [
                    f"/serve-file/{course_name}/{week}/{f['filename']}"
                    for f in file_list
                ]
            return jsonify({"material": material})
        else:
            course_name = request.args.get("course")
            if not course_name:
                return jsonify({"error": "No course specified"}), 400

            course_path = os.path.join(COURSE_MATERIAL_DIR, course_name)
            if not os.path.exists(course_path):
                return jsonify({"error": "Course not found"}), 404

            material = {}

            for week_folder in os.listdir(course_path):
                week_path = os.path.join(course_path, week_folder)
                if os.path.isdir(week_path) and week_folder.isdigit():
                    files = os.listdir(week_path)
                    file_urls = [
                        f"/serve-file/{course_name}/{week_folder}/{file}"  # Updated URL pattern
                        for file in files
                    ]
                    material[week_folder] = file_urls

            return jsonify({"material": material})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get-student-chat-history", methods=["POST"])
def get_student_chat_history():
    try:
        data = request.json
        student_id = data.get("student_id")
        if not student_id:
            return jsonify({"error": "Student ID is required"}), 400

        conversations = chat_history_mongodb.get_chat_history_by_student_id(student_id)

        return jsonify(
            {
                "student_id": student_id,
                "conversation_count": len(conversations),
                "conversations": conversations,
            }
        )

    except Exception as e:
        logging.error(f"Error in get_user_chat_history: {str(e)}", exc_info=True)
        return (
            jsonify({"error": "Failed to retrieve chat history", "details": str(e)}),
            500,
        )


@app.route("/serve-file/<course>/<week>/<filename>")
def serve_file(course, week, filename):
    file_path = os.path.join(COURSE_MATERIAL_DIR, course, week)
    return send_from_directory(file_path, filename)


@app.route("/add-course", methods=["POST"])
def add_course():
    try:
        data = request.json
        course_code = data.get("course_code")
        course_name = data.get("course_name")

        # Validate input
        if not course_code or not course_name:
            return jsonify({"error": "Course code and name are required"}), 400

        # Replace spaces in course name with underscores
        formatted_course_name = course_name.replace(" ", "_")
        folder_name = f"{course_code}_{formatted_course_name}"

        if use_mongodb:
            result = rag.add_course_to_structure(folder_name)
            if result["success"]:
                return jsonify({"message": result["message"]}), 200
            else:
                return jsonify({"error": result["message"]}), 400
        else:
            course_path = os.path.join("course_material", folder_name)

            # Create the main course folder
            os.makedirs(course_path, exist_ok=True)

            # Create 14 subfolders for weekly content
            for week in range(1, 15):
                week_folder = os.path.join(course_path, str(week))
                os.makedirs(week_folder, exist_ok=True)

            return (
                jsonify(
                    {"message": "Course folder and subfolders created successfully"}
                ),
                200,
            )
    except Exception as e:
        # Log the error for debugging
        print(f"Error in /api/add-course: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/rename-item", methods=["POST"])
def rename_item():
    try:
        data = request.json
        print("Received rename request:", data)  # Log the request data
        item_type = data.get("type")  # "course", "week", or "file"
        old_path = data.get("old_path")
        new_name = data.get("new_name")

        # Validate input
        if not item_type or not old_path or not new_name:
            return jsonify({"error": "Missing required parameters"}), 400

        # Construct the full old and new paths
        if item_type == "course":
            base_path = os.path.join("course_material", old_path)
            new_path = os.path.join("course_material", new_name)
        elif item_type == "week":
            # Split the old_path into course_name and week_number
            course_name, week_number = old_path.split("/")
            base_path = os.path.join("course_material", course_name, week_number)
            new_path = os.path.join("course_material", course_name, new_name)
        elif item_type == "file":
            # Split the old_path into course_name, week_number, and filename
            parts = old_path.split("/")
            if len(parts) != 3:
                return jsonify({"error": "Invalid file path format"}), 400
            course_name, week_number, filename = parts
            base_path = os.path.join(
                "course_material", course_name, week_number, filename
            )
            new_path = os.path.join(
                "course_material", course_name, week_number, new_name
            )
        else:
            return jsonify({"error": "Invalid item type"}), 400

        # Check if the old path exists
        if not os.path.exists(base_path):
            return jsonify({"error": f"{item_type.capitalize()} not found"}), 404

        # Rename the item
        os.rename(base_path, new_path)
        return (
            jsonify({"message": f"{item_type.capitalize()} renamed successfully"}),
            200,
        )
    except Exception as e:
        print(f"Error renaming {item_type}: {str(e)}")
        return jsonify({"error": f"Failed to rename {item_type}"}), 500


@app.route("/delete-item", methods=["POST"])
def delete_item():
    try:
        data = request.json
        item_type = data.get("type")  # "course", "week", or "file"
        print(f"item_type: {item_type}")
        path = data.get("path")
        print(f"path for deletion: {path}")
        if use_mongodb:
            # delete course material from mongodb
            if item_type == "course":
                # get course name from path
                course_name = path.split("/")[-1]
                # delete course material from mongodb
                result = rag.delete_by_course(course_name)
            elif item_type == "week":
                # get course name and week number from path
                course_name, week_number = path.split("/")[-2:]
                # delete course material from mongodb
                result = rag.delete_by_week(course_name, int(week_number))
            elif item_type == "file":
                # get course name, week number, and filename from path
                course_name, week_number, filename = path.split("/")[-3:]
                print(f"course_name: {course_name}")
                print(f"week_number: {week_number}")
                print(f"filename: {filename}")
                # delete course material from mongodb
                result = rag.delete_by_file(course_name, int(week_number), filename)

            if not result:
                return jsonify({"error": "Failed to delete material"}), 500

            if result["acknowledged"]:
                result["message"] = f"{item_type.capitalize()} deleted successfully"
                return jsonify(result), 200
            else:
                return jsonify(result), 500
        else:
            if not item_type or not path:
                return jsonify({"error": "Missing required parameters"}), 400

            # Construct the full path
            full_path = os.path.join("course_material", path)

            # Check if the path exists
            if not os.path.exists(full_path):
                return jsonify({"error": f"{item_type.capitalize()} not found"}), 404

            # Delete the item
            if item_type == "course":
                shutil.rmtree(full_path)  # Delete the entire course folder
            elif item_type == "week":
                shutil.rmtree(full_path)  # Delete the entire week folder
            elif item_type == "file":
                os.remove(full_path)  # Delete a single file
            else:
                return jsonify({"error": "Invalid item type"}), 400

            return (
                jsonify({"message": f"{item_type.capitalize()} deleted successfully"}),
                200,
            )
    except Exception as e:
        print(f"Error deleting {item_type}: {str(e)}")
        return jsonify({"error": f"Failed to delete {item_type}"}), 500


@app.route("/upload-file", methods=["POST"])
def upload_file():
    try:
        course_name = request.form.get("course_name")
        week_number = request.form.get("week_number")

        print(f"course_name: {course_name}")
        print(f"week_number: {week_number}")
        file = request.files.get("file")

        if not course_name or not week_number or not file:
            return jsonify({"error": "Missing required parameters"}), 400

        if use_mongodb:
            # create temporary folder to save file
            # Create a project-specific temp directory
            project_temp_dir = "./temp"  # Relative to current working directory

            # Create the directory if it doesn't exist
            if not os.path.exists(project_temp_dir):
                os.makedirs(project_temp_dir)
            # Use this as the base for your temporary directories
            with tempfile.TemporaryDirectory(dir=project_temp_dir) as temp_dir:
                print(f"Created temp directory: {temp_dir}")
                # save file to temp directory
                file.save(os.path.join(temp_dir, file.filename))
                # embed documents
                embed_documents_mongodb(
                    course_name,
                    temp_dir,
                    int(week_number),
                )

        else:
            # Save the file to the appropriate week folder
            upload_path = os.path.join(
                "course_material", course_name, week_number, file.filename
            )
            file.save(upload_path)

        return jsonify({"message": "File uploaded successfully"}), 200
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return jsonify({"error": "Failed to upload file"}), 500


@app.route("/edit-week-topic", methods=["PUT"])
def edit_week_topic():
    try:
        data = request.json
        course_name = data.get("course_name")
        week_number = data.get("week_number")
        topic_name = data.get("topic_name")

        if use_mongodb:
            result = rag.edit_week_topic(course_name, int(week_number), topic_name)
            return jsonify({"message": f"Week topic updated successfully"}), 200
        else:
            return jsonify({"error": "Only supported for MongoDB"}), 500
    except Exception as e:
        print(f"Error editing week topic: {str(e)}")
        return jsonify({"error": "Failed to edit week topic"}), 500


# Function to update access time for a vector store
def update_vector_store_access_time(thread_id):
    """Update the last access time for a thread's vector store"""
    app.vector_store_access_times[thread_id] = datetime.now()


# Function to clean up expired vector stores
def cleanup_vector_stores():
    """Remove vector stores for expired sessions to prevent memory leaks"""
    if not hasattr(app, "vector_store_access_times"):
        return

    # First clean up based on access time
    current_time = datetime.now()
    expired_time = current_time - timedelta(
        hours=2
    )  # Sessions older than 2 hours expire

    to_remove = []
    for thread_id, last_access in app.vector_store_access_times.items():
        if last_access < expired_time:
            to_remove.append(thread_id)

    for thread_id in to_remove:
        if thread_id in app.vector_stores:
            del app.vector_stores[thread_id]
        if thread_id in app.vector_store_access_times:
            del app.vector_store_access_times[thread_id]

    if to_remove:
        logging.info(f"Cleaned up {len(to_remove)} expired vector stores based on time")

    # Then check for orphaned vector stores that might exist in app.vector_stores
    # but not be accessible in MongoDB (thread no longer exists)
    orphaned = []

    # Collect all thread_ids from MongoDB
    try:

        # Get existing thread IDs from MongoDB
        existing_thread_ids = chat_history_mongodb.get_all_threads()

        # Find thread IDs that have vector stores but don't exist in MongoDB
        for thread_id in list(app.vector_stores.keys()):
            if thread_id not in existing_thread_ids:
                orphaned.append(thread_id)

        # Remove orphaned vector stores
        for thread_id in orphaned:
            if thread_id in app.vector_stores:
                del app.vector_stores[thread_id]
            if thread_id in app.vector_store_access_times:
                del app.vector_store_access_times[thread_id]

        if orphaned:
            logging.info(f"Cleaned up {len(orphaned)} orphaned vector stores")
    except Exception as e:
        logging.error(f"Error checking for orphaned vector stores: {str(e)}")


# Set up scheduled cleanup task to run every hour
def scheduled_cleanup():
    """Run cleanup tasks periodically"""
    while True:
        try:
            time.sleep(3600)  # Sleep for 1 hour
            with app.app_context():
                cleanup_vector_stores()
        except Exception as e:
            logging.error(f"Error in scheduled cleanup: {str(e)}")


def _get_all_session_files():
    return [
        os.path.join(SESSION_HISTORY_DIR, f)
        for f in os.listdir(SESSION_HISTORY_DIR)
        if f.endswith(".txt")
    ]


def _get_session_files_by_student(student_id: str):
    return [
        os.path.join(SESSION_HISTORY_DIR, f)
        for f in os.listdir(SESSION_HISTORY_DIR)
        if f.endswith(f"_{student_id}.txt")
    ]


def _get_session_files_by_course(course_code: str):
    return [
        os.path.join(SESSION_HISTORY_DIR, f)
        for f in os.listdir(SESSION_HISTORY_DIR)
        if f.split("_")[2] == course_code
    ]


def _get_session_files_by_date(date: str):
    return [
        os.path.join(SESSION_HISTORY_DIR, f)
        for f in os.listdir(SESSION_HISTORY_DIR)
        if f.startswith(date)
    ]


def _combine_session_files(session_files: list):
    combined_content = ""
    for filepath in session_files:
        try:
            with open(filepath, "r") as file:
                combined_content += file.read() + "\n"
        except Exception as e:
            logging.error(f"Error reading file {filepath}: {str(e)}")
    return combined_content


def _combine_conversation_messages(conversations: list[dict]) -> str:
    """
    Convert a conversation's messages to a single string.

    Args:
        conversation (dict): A conversation dictionary containing 'messages' key

    Returns:
        str: A string representation of all messages in the conversation
    """
    if not conversations:
        return ""

    result = ""

    for index, conversation in enumerate(conversations):
        if (
            len(conversation["messages"]) < 2
        ):  # Skip if there is only one conversation (no student response)
            continue

        result += f"Conversation {index + 1}"
        for message in conversation["messages"]:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            result += f"[{role.upper()}]: {content}\n\n"
        result += "\n\n"

    return result


def _get_session_data():
    # Get session data
    session_data = chat_history_mongodb.get_all_session_data()

    # session_files = _get_all_session_files()
    # for filepath in session_files:
    #     filename = os.path.basename(filepath)
    #     parts = filename.split("_")
    #     if len(parts) == 4:
    #         date, time, course_code, student_id = parts
    #         student_id = student_id.split(".")[0]  # Remove .txt
    #         session_data.append(
    #             {
    #                 "date": date,
    #                 "time": time,
    #                 "course_code": course_code,
    #                 "student_id": student_id,
    #             }
    #         )
    return session_data


# Start the cleanup thread
if not use_mongodb:
    cleanup_thread = threading.Thread(target=scheduled_cleanup, daemon=True)
    cleanup_thread.start()


# Run the Flask app
if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 5001)),
        debug=os.getenv("FLASK_DEBUG", "True").lower() == "true",
    )
