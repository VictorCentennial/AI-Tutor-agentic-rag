// TutorChat.jsx
import { useState } from "react";
import { Container } from "react-bootstrap";
import TutorStart from "./TutorStart";
import TutorInteraction from "./TutorInteraction";
import axios from "axios";
import "../App.css"; // Adjust the import path if necessary

function TutorChat() {
  const [isLoading, setIsLoading] = useState(false)
  const [aiMessages, setAiMessages] = useState([]);
  const [llmPrompt, setLlmPrompt] = useState(""); // To display the LLM prompt for debugging
  const [isTutoringStarted, setIsTutoringStarted] = useState(false);
  // const [subject, setSubject] = useState(""); // State variable for subject
  // const [topic, setTopic] = useState("");     // State variable for topic
  // const [duration, setDuration] = useState(30); // State variable for duration
  const [threadId, setThreadId] = useState(""); // State variable for threadId
  // Function to handle the start of the tutoring session
  const [nextState, setNextState] = useState("");

  const handleStartTutoring = async (selectedFolder, selectedDuration) => {
    try {
      // setSubject(selectedSubject); // Store the selected subject in state
      // setTopic(selectedTopic);     // Store the selected topic in state
      // setDuration(selectedDuration); // Store the selected duration in state
      // setAiMessages([]);
      // Reset aiMessages to clear any previous messages
      setIsLoading(true);
      const response = await axios.post("api/start-tutoring", {
        folder_name: selectedFolder,
        duration: selectedDuration,
        //file_name: "topic_material.txt", // Adjust the file name if necessary
      });
      setIsLoading(false);

      // // Debug logs
      // console.log('Full response:', response);
      // console.log('Response data:', response.data);
      // console.log('response.data.messages:', response.data.messages);

      const messages = response.data.messages;
      setThreadId(response.data.thread_id);
      //const llmPrompt = response.data.prompt; // Extract the prompt sent to the LLM
      setAiMessages(messages);


      const state = response.data.state;
      setLlmPrompt(state);
      setNextState(response.data.next_state);

      console.log(`state: ${state}`);

      //setAiMessages([{ sender: aiResponse.role, message: aiResponse.content }]);

      //setAiMessages([{ sender: "AI", message: aiResponse }]);
      //setLlmPrompt(llmPrompt); // Display the prompt in the LLM Prompt box
      setIsTutoringStarted(true); // Mark that the tutoring session has started
    } catch (error) {
      console.error("Error starting tutoring session:", error);
    }
  };

  const handleSend = async (userMessage) => {
    try {

      setAiMessages([...aiMessages, { role: "User", content: userMessage }]);
      setIsLoading(true);
      const response = await axios.post("api/continue-tutoring", {
        student_response: userMessage,
        thread_id: threadId,
      });
      //const aiResponse = response.data.response;
      const { messages, state, next_state } = response.data;
      //const llmPrompt = response.data.prompt || ""; // Extract the prompt sent to the LLM if available
      //const llmPrompt = response.data.state;
      // console.log("messages:", messages);
      setIsLoading(false);
      setAiMessages(messages);
      setLlmPrompt(state);
      console.log(`state: ${state}`);
      setNextState(next_state);


      // setAiMessages((prevMessages) => [
      //   messages.map((message) => ({
      //     sender: message.role,
      //     message: message.content,
      //   })),
      // ...prevMessages,
      // { sender: "User", message: userMessage },
      // { sender: "AI", message: aiResponse },
      // ]);
      //setLlmPrompt(llmPrompt); // Display the prompt in the LLM Prompt box if available
    } catch (error) {
      console.error("Error continuing tutoring session:", error);
    }
  }
  return (
    <Container fluid className="mt-4">
      {!isTutoringStarted ? (
        <TutorStart onStartTutoring={handleStartTutoring} isLoading={isLoading} />
      ) : (
        <TutorInteraction
          aiMessages={aiMessages}
          llmPrompt={llmPrompt}
          onSend={handleSend}
          isLoading={isLoading}
          nextState={nextState}
        />
      )}
    </Container>
  );
}

export default TutorChat;
