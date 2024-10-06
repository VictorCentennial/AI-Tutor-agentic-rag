// TutorChat component to handle the tutoring session
import React, { useState } from "react";
import { Container } from "react-bootstrap";
import TutorStart from "./TutorStart";
import TutorInteraction from "./TutorInteraction";
import axios from "axios";
import "../App.css"; // Correct import path for CSS file

function TutorChat() {
  const [aiMessages, setAiMessages] = useState([]);
  const [llmPrompt, setLlmPrompt] = useState(""); // To display the LLM prompt for debugging
  const [isTutoringStarted, setIsTutoringStarted] = useState(false);

  const handleStartTutoring = async (subject, topic) => {
    try {
      const response = await axios.post("api/start-tutoring", {
        topic,
        file_name: "topic_material.txt", // Assuming you use the same file for testing
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
      });
      const aiResponse = response.data.response;
      const llmPrompt = response.data.prompt; // Extract the prompt sent to the LLM
  
      setAiMessages((prevMessages) => [
        ...prevMessages,
        { sender: "User", message: userMessage },
        { sender: "AI", message: aiResponse },
      ]);
      setLlmPrompt(llmPrompt); // Display the prompt in the LLM Prompt box
    } catch (error) {
      console.error("Error continuing tutoring session:", error);
    }
  };

  return (
    <Container fluid className="mt-4">
      {!isTutoringStarted ? (
        <TutorStart onStartTutoring={handleStartTutoring} />
      ) : (
        <TutorInteraction aiMessages={aiMessages} llmPrompt={llmPrompt} onSend={handleSend} />
      )}
    </Container>
  );
}

export default TutorChat;
