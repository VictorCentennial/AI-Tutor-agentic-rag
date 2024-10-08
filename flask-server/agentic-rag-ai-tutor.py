# app_flask_ai_tutor.py - Updated Flask API for Agentic RAG AI Tutor using Gemini API and LangChain with RunnableSequence

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
import re

# Import LangChain components
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnableSequence

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

# Set up ConversationBufferMemory for managing session context
memory = ConversationBufferMemory(memory_key="conversation_history", return_messages=True)

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
7. **Provide Feedback:** Correct misconceptions and acknowledge correct understanding.

Follow these instructions strictly. Do not add information not included in the provided materials or the topic.
""",
    # Add other subjects as needed
}

# Meta-Agent to dynamically delegate tasks to other agents
class MetaAgent:
    def __init__(self, agents, memory):
        self.agents = agents
        self.memory = memory
        self.current_agent = self.agents['Welcome']  # Starts with WelcomeAgent

    def delegate_task(self, student_response, context):
        # Use a more flexible condition to move to TutorAgent, such as keywords like "learn", "understand", etc.
        if "learn" in student_response.lower() or "understand" in student_response.lower():
            self.current_agent = self.agents['Tutor']
        elif "summarize" in student_response.lower() or "done" in student_response.lower():
            self.current_agent = self.agents['Summary']
        return self.current_agent.handle_task(student_response, context, self.memory)

# Define different agents
class WelcomeAgent:
    def handle_task(self, student_response, context, memory):
        return "Welcome to your Java tutoring session. Can you tell me what you're hoping to learn today?"

class TutorAgent:
    def handle_task(self, student_response, context, memory):
        return f"Let's dive into {student_response}. Here’s what I found from the course materials: {context}"

class SummaryAgent:
    def handle_task(self, student_response, context, memory):
        return "Great job! Here's a summary of what we covered in this session."

# Define agents
agents = {
    'Welcome': WelcomeAgent(),
    'Tutor': TutorAgent(),
    'Summary': SummaryAgent()
}

meta_agent = MetaAgent(agents, memory)

# Function to load document content using LangChain
def load_document_content(file_path):
    try:
        # Load documents from the file using TextLoader
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
    initial_instruction = "Your first message should be a greeting to the student and an open-ended question about the topic to assess their current understanding."

    # Combine subject, topic, and context into one input string for the prompt
    input_string = f"{tutor_instructions}\n\n{initial_instruction}\n\nTopic: {topic}\n\nContext:\n{context}"

    # Log the conversation start for debugging
    logging.debug(f"Starting conversation on subject: {subject}, topic: {topic} with context from {file_name}")

    # Initialize the prompt template
    tutor_prompt = PromptTemplate.from_template("{input}")

    # Create a RunnableSequence chain
    tutor_chain = RunnableSequence(tutor_prompt, llm)
    
    # Invoke the sequence
    response = tutor_chain.invoke({"input": input_string})

    # Access the content of the AIMessage object and strip whitespace
    ai_response_content = response.content.strip()

    # Save the response in the memory
    memory.chat_memory.add_ai_message(ai_response_content)

    # Include the input string (LLM prompt) in the response
    return jsonify({"response": ai_response_content, "prompt": input_string})



# API endpoint to handle student responses and continue the session
@app.route('/continue-tutoring', methods=['POST'])
def continue_tutoring():
    data = request.json
    student_response = data.get('student_response', '')
    subject = data.get('subject', 'Java')
    topic = data.get('topic', 'Polymorphism in Java')

    # Load context content
    file_name = 'topic_material.txt'
    file_path = os.path.join("data", file_name)
    context = load_document_content(file_path)

    # Use MetaAgent to handle the flow of the session
    ai_response_content = meta_agent.delegate_task(student_response, context)

    # Save the AI response into memory
    memory.chat_memory.add_ai_message(ai_response_content)

    # Return the latest AI response
    return jsonify({"response": ai_response_content})

# API endpoint to collect student feedback for RLHF
@app.route('/feedback', methods=['POST'])
def collect_feedback():
    data = request.json
    rating = data.get('rating', None)
    conversation_history = memory.chat_memory.messages

    # Store feedback (this can later be used for RLHF integration)
    logging.debug(f"Feedback received: Rating {rating} for conversation {conversation_history}")

    # Placeholder for RLHF logic (adjust LLM based on feedback)
    # Here we can store the feedback and use it for reinforcement learning updates

    return jsonify({"message": "Feedback received. Thank you!"})

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
