// TutorChat.jsx
import React, { useState } from "react";
import { Container } from "react-bootstrap";
import TutorStart from "./TutorStart";
import TutorInteraction from "./TutorInteraction";
import axios from "axios";
import "../App.css"; // Adjust the import path if necessary

function TutorChat() {
  const [aiMessages, setAiMessages] = useState([]);
  const [llmPrompt, setLlmPrompt] = useState(""); // To display the LLM prompt for debugging
  const [isTutoringStarted, setIsTutoringStarted] = useState(false);
  const [subject, setSubject] = useState(""); // State variable for subject
  const [topic, setTopic] = useState("");     // State variable for topic

  const handleStartTutoring = async (selectedSubject, selectedTopic) => {
    try {
      setSubject(selectedSubject); // Store the selected subject in state
      setTopic(selectedTopic);     // Store the selected topic in state
      setAiMessages([]);           // Reset aiMessages to clear any previous messages

      const response = await axios.post("api/start-tutoring", {
        subject: selectedSubject,
        topic: selectedTopic,
        file_name: "topic_material.txt", // Adjust the file name if necessary
      });

      const aiResponse = response.data.response;
      const llmPrompt = response.data.prompt; // Extract the prompt sent to the LLM

      setAiMessages([{ sender: "AI", message: aiResponse }]);
      setLlmPrompt(llmPrompt); // Display the prompt in the LLM Prompt box
      setIsTutoringStarted(true); // Mark that the tutoring session has started
    } catch (error) {
      console.error("Error starting tutoring session:", error);
    }
  };

  const handleSend = async (userMessage) => {
    try {
      const response = await axios.post("api/continue-tutoring", {
        student_response: userMessage,
        subject, // Include subject from state
        topic,   // Include topic from state
      });
      const aiResponse = response.data.response;
      const llmPrompt = response.data.prompt || ""; // Extract the prompt sent to the LLM if available

      setAiMessages((prevMessages) => [
        ...prevMessages,
        { sender: "User", message: userMessage },
        { sender: "AI", message: aiResponse },
      ]);
      setLlmPrompt(llmPrompt); // Display the prompt in the LLM Prompt box if available
    } catch (error) {
      console.error("Error continuing tutoring session:", error);
    }
  };

  return (
    <Container fluid className="mt-4">
      {!isTutoringStarted ? (
        <TutorStart onStartTutoring={handleStartTutoring} />
      ) : (
        <TutorInteraction
          aiMessages={aiMessages}
          llmPrompt={llmPrompt}
          onSend={handleSend}
        />
      )}
    </Container>
  );
}

export default TutorChat;
