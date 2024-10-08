# app_flask_ai_tutor.py - Updated Flask API for AI Tutoring System

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
import re

# Import additional libraries for embeddings
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Import LangChain components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-pro")  # Use "gemini-pro" or your model name

# Initialize the LLM with the correct model
llm = ChatGoogleGenerativeAI(model=GOOGLE_MODEL_NAME, google_api_key=GOOGLE_API_KEY)

# Load the pre-trained Sentence Transformer model
# Consider using a more advanced model for better semantic understanding
embedding_model = SentenceTransformer('all-mpnet-base-v2')  # Updated model

# Define subject-specific tutor instructions
subject_instructions = {
    "Java": """
You are a friendly, encouraging AI tutor specializing in Java programming. Your goal is to help students understand Java concepts by guiding them through structured learning.

1. **Initiate the Conversation:** Start by greeting the student and asking an open-ended question to assess their current understanding of the topic.
2. **Wait for the Student's Response:** Do not proceed or provide additional information until the student responds.
3. **Provide Clear Explanations:** Use the provided context materials to explain the topic step by step, based on the student's responses.
4. **Ask Open-Ended Questions:** Encourage the student to think critically and explain their understanding.
5. **Offer Adaptive Hints:** If the student struggles, provide hints that guide them without giving away answers.
6. **Stay On-Topic:** If the student asks off-topic questions, politely redirect them back to the topic.
7. **Do Not Generate Student Messages:** Do not create or include messages on behalf of the student. Only provide your own responses.
8. **Provide Feedback:** Correct misconceptions and acknowledge correct understanding.

Follow these instructions strictly. Do not add information not included in the provided materials or the topic.
""",
    # Add other subjects as needed
}

# Use ConversationBufferMemory to manage tutoring sessions
memory = ConversationBufferMemory(memory_key="conversation_history", return_messages=True)

# Function to load document content using DocumentLoader
def load_document_content(file_path):
    try:
        # Load documents from the file using a TextLoader
        loader = TextLoader(file_path)
        documents = loader.load()

        # Split text into smaller chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents(documents)

        # Concatenate the chunks into a single context string
        context = "\n".join([doc.page_content for doc in docs])
        return context
    except Exception as e:
        return f"Error loading document content: {e}"

# Function to check if the student response is relevant to the topic
def is_relevant_response(student_response, topic, context):
    try:
        # Combine topic and context
        topic_context = topic + " " + context
        topic_embedding = embedding_model.encode(topic_context, convert_to_tensor=True)
        response_embedding = embedding_model.encode(student_response, convert_to_tensor=True)

        # Compute cosine similarity
        similarity = cosine_similarity(
            topic_embedding.cpu().numpy().reshape(1, -1),
            response_embedding.cpu().numpy().reshape(1, -1)
        )[0][0]

        logging.debug(f"Semantic similarity: {similarity}")

        # Set a lower threshold for relevance (adjust as necessary)
        return similarity > 0.3
    except Exception as e:
        logging.error(f"Error in relevance detection: {e}")
        # If there's an error, assume the response is relevant to avoid false negatives
        return True

# Function to extract only the assistant's response from the AI's output
def extract_assistant_response(ai_response):
    # Remove any user messages if present
    user_patterns = ["User:", "Student:", "Question:", "You:"]
    for pattern in user_patterns:
        if pattern in ai_response:
            # Keep content before the pattern
            ai_response = ai_response.split(pattern, 1)[0].strip()
    # Remove any labels like "Assistant:" or "Tutor:"
    assistant_patterns = ["Assistant:", "AI:", "Tutor:"]
    for pattern in assistant_patterns:
        ai_response = ai_response.replace(pattern, "").strip()
    return ai_response

# API endpoint to start a tutoring session
@app.route('/start-tutoring', methods=['POST'])
def start_tutoring():
    data = request.json
    subject = data.get('subject', 'Java')
    topic = data.get('topic', 'Polymorphism in Java')
    file_name = data.get('file_name', 'topic_material.txt')
    file_path = os.path.join("data", file_name)

    # Clear the conversation memory at the start of a new session
    memory.chat_memory.clear()

    # Load context content from the document
    context = load_document_content(file_path)

    if context.startswith("Error"):
        return jsonify({"error": context}), 400

    # Retrieve subject-specific instructions
    tutor_instructions = subject_instructions.get(subject, subject_instructions["Java"])

    # Add a specific instruction for the initial message
    initial_instruction = "Your first message should be a greeting to the student and an open-ended question about the topic to assess their current understanding. Do not include any other information."

    # Combine subject, topic, and context into one input string for the prompt
    input_string = f"{tutor_instructions}\n\n{initial_instruction}\n\nTopic: {topic}\n\nContext:\n{context}"

    # Log the conversation start for debugging
    logging.debug(f"Starting conversation on subject: {subject}, topic: {topic} with context from {file_name}")

    # Initialize the prompt template
    tutor_prompt = PromptTemplate.from_template("{input}")

    # Run the chain with the combined input
    tutor_chain = tutor_prompt | llm
    response = tutor_chain.invoke({"input": input_string})

    # Extract the content from the AIMessage (response is an AIMessage object)
    ai_response_content = response.content.strip()

    # Extract only the assistant's response
    ai_response_content = extract_assistant_response(ai_response_content)

    logging.debug(f"Initial AI Response: {ai_response_content}")

    # Initialize the conversation with the first AI message
    memory.chat_memory.add_ai_message(ai_response_content)
    memory.save_context({"input": input_string}, {"output": ai_response_content})

    # Include the input string (LLM prompt) in the response
    return jsonify({"response": ai_response_content, "prompt": input_string})

# API endpoint to handle student responses and continue the session
@app.route('/continue-tutoring', methods=['POST'])
def continue_tutoring():
    data = request.json
    student_response = data.get('student_response', '')
    subject = data.get('subject', 'Java')
    topic = data.get('topic', 'Polymorphism in Java')

    # If the student's response is empty, return an error message
    if not student_response.strip():
        logging.debug("Empty student input, asking for clarification.")
        return jsonify({"response": "Please enter your response or question."}), 400

    # Load context content
    file_name = 'topic_material.txt'  # This should be maintained per session
    file_path = os.path.join("data", file_name)
    context = load_document_content(file_path)

    # Check if the student's response is relevant to the topic
    if not is_relevant_response(student_response, topic, context):
        ai_response_content = f"Let's stay focused on '{topic}'. Could you please share your thoughts or questions about this topic?"
        memory.chat_memory.add_ai_message(ai_response_content)
        logging.debug("Student response was off-topic. Redirecting the conversation.")
        return jsonify({"response": ai_response_content})

    # Add the student's response to the conversation memory
    memory.chat_memory.add_user_message(student_response)
    logging.debug(f"User said: {student_response}")

    # Retrieve subject-specific instructions
    tutor_instructions = subject_instructions.get(subject, subject_instructions["Java"])

    # Retrieve the entire conversation history
    conversation_history = "\n".join([f"{msg.type.capitalize()}: {msg.content}" for msg in memory.chat_memory.messages])

    # Format the input for the prompt
    input_string = f"{tutor_instructions}\n\nTopic: {topic}\n\nContext:\n{context}\n\nConversation History:\n{conversation_history}\n\nProvide only your response as the tutor."

    # Log the input string
    logging.debug(f"Formatted Input String for LLM:\n{input_string}")

    # Initialize the prompt template
    tutor_prompt = PromptTemplate.from_template("{input}")

    # Run the LLM with the conversation history as context
    tutor_chain = tutor_prompt | llm
    response = tutor_chain.invoke({"input": input_string})

    # Extract the AI response
    ai_response_content = response.content.strip()

    # Extract only the assistant's response
    ai_response_content = extract_assistant_response(ai_response_content)

    logging.debug(f"AI Response: {ai_response_content}")

    # Save the AI response into memory
    memory.chat_memory.add_ai_message(ai_response_content)

    # Return the latest AI response
    return jsonify({"response": ai_response_content})

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
