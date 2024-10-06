from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize the LLM with Gemini API
llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY)

# Define the updated tutor instructions with stricter interaction control
tutor_instructions = """
You are a friendly, encouraging AI tutor for software engineering students. Your goal is to help students understand concepts by guiding them through structured learning.
1. Ask the student what they want to learn about and wait for their response.
2. Based on the student's response, ask them what they already know about the chosen topic.
3. Use the provided context materials to explain the topic clearly, step by step, while asking questions and waiting for the student to respond.
4. Do not generate responses unless the student has given input. Wait for them to ask questions or provide an answer before proceeding.
5. Always refer back to the provided material, and do not add any information that is not in the material.
6. If the student struggles, offer hints or explanations, but do not proceed without their response.

Context:
{input}

Follow these instructions strictly. Do not make assumptions or ask further questions unless the student explicitly provides input.
"""

# Use ConversationBufferMemory to manage tutoring sessions
memory = ConversationBufferMemory(memory_key="conversation_history", return_messages=True)

# Update the prompt to accept both topic and context as a single input string
tutor_prompt = PromptTemplate.from_template(tutor_instructions)

# Instead of LLMChain, use the new recommended pattern with RunnableSequence
tutor_chain = tutor_prompt | llm

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

# API endpoint to start a tutoring session
@app.route('/start-tutoring', methods=['POST'])
def start_tutoring():
    data = request.json
    subject = data.get('subject', 'Java')  # Retrieve selected subject
    topic = data.get('topic', 'Software Engineering')
    file_name = data.get('file_name', 'topic_material.txt')
    file_path = os.path.join("data", file_name)

    # Load context content from the document
    context = load_document_content(file_path)

    if context.startswith("Error"):
        return jsonify({"error": context}), 400

    # Combine subject, topic, and context into one input string for the prompt
    input_string = f"Subject: {subject}\nTopic: {topic}\nContext: {context}"

    # Log the conversation start for debugging
    logging.debug(f"Starting conversation on subject: {subject}, topic: {topic} with context from {file_name}")

    # Run the chain with the combined input
    response = tutor_chain.invoke({"input": input_string, "subject": subject})

    # Extract the content from the AIMessage (response is an AIMessage object)
    ai_response_content = response.content

    logging.debug(f"Initial AI Response: {ai_response_content}")

    # Initialize the conversation with the first AI message
    memory.chat_memory.add_ai_message(ai_response_content)
    
    # Include the input string (LLM prompt) in the response
    return jsonify({"response": ai_response_content, "prompt": input_string})


# API endpoint to handle student responses and continue the session
@app.route('/continue-tutoring', methods=['POST'])
def continue_tutoring():
    data = request.json
    student_response = data.get('student_response', '')
    subject = data.get('subject', 'Java')  # Retrieve selected subject

    # If the student's response is empty, return an error message
    if not student_response.strip():
        logging.debug("Empty student input, asking for clarification.")
        return jsonify({"response": "Please enter your response or question."}), 400

    # Add the student's response to the conversation memory
    memory.chat_memory.add_user_message(student_response)
    logging.debug(f"User said: {student_response}")

    # Retrieve the entire conversation history
    conversation_history = "\n".join([f"User: {msg.content}" if msg.type == "human" else f"AI: {msg.content}" for msg in memory.chat_memory.messages])

    # Refresh the rules every 3 interactions to remind the AI of its role
    if len(memory.chat_memory.messages) % 6 == 0:  # After every 3 user-AI interactions
        conversation_history = f"{tutor_instructions}\n\n{conversation_history}"
        logging.debug("Reintroducing tutor instructions into the conversation.")

    logging.debug(f"Formatted Conversation History for Context: {conversation_history}")
    
    # Run the LLM with the conversation history as context
    response = tutor_chain.invoke({"input": conversation_history, "subject": subject})

    # Extract only the new AI response
    ai_response_content = response.content

    logging.debug(f"AI Response: {ai_response_content}")

    # Save the AI response into memory
    memory.chat_memory.add_ai_message(ai_response_content)

    # Include the conversation history (prompt sent to LLM) in the response
    #return jsonify({"response": ai_response_content, "prompt": conversation_history})
    # Return only the latest AI response, not the entire conversation history
    return jsonify({"response": ai_response_content})


# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
