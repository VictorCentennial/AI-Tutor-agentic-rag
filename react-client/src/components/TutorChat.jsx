import { useState, useEffect } from "react";
import { Container, Modal } from "react-bootstrap";
import TutorStart from "./TutorStart";
import TutorInteraction from "./TutorInteraction";
import axios from "axios";
import "../App.css";

function TutorChat() {
  const [isLoading, setIsLoading] = useState(false);
  const [aiMessages, setAiMessages] = useState([]);
  const [llmPrompt, setLlmPrompt] = useState("");
  const [isTutoringStarted, setIsTutoringStarted] = useState(false);
  const [threadId, setThreadId] = useState("");
  const [nextState, setNextState] = useState("");
  const [remainingTime, setRemainingTime] = useState(0); // State for remaining time in seconds
  const [showWarning, setShowWarning] = useState(false); // State for pop-up visibility

  useEffect(() => {
    if (remainingTime > 0 && isTutoringStarted) {
      const timer = setInterval(() => {
        setRemainingTime((prev) => prev - 1);
      }, 1000);

      // Show warning pop-up when 5 minutes (300 seconds) are left
      if (remainingTime === 300) {
        setShowWarning(true);
      }

      return () => clearInterval(timer);
    }
  }, [remainingTime, isTutoringStarted]);

  const handleStartTutoring = async (selectedFolder, selectedDuration) => {
    try {
      setIsLoading(true);
      const response = await axios.post("api/start-tutoring", {
        folder_name: selectedFolder,
        duration: selectedDuration,
      });
      setIsLoading(false);

      const messages = response.data.messages;
      setThreadId(response.data.thread_id);
      setAiMessages(messages);

      const state = response.data.state;
      setLlmPrompt(state);
      setNextState(response.data.next_state);

      setIsTutoringStarted(true);
      setRemainingTime(selectedDuration * 60); // Convert minutes to seconds
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
      const { messages, state, next_state } = response.data;
      setIsLoading(false);
      setAiMessages(messages);
      setLlmPrompt(state);
      setNextState(next_state);
    } catch (error) {
      console.error("Error continuing tutoring session:", error);
    }
  };

  const formatTime = (timeInSeconds) => {
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = timeInSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  return (
    <Container fluid className="mt-4 relative w-full">
      {isTutoringStarted && (
        <div
          className={`absolute right-0 top-0 px-4 py-2 rounded-md text-right ${
            remainingTime <= 300 && remainingTime !== 0 ? "blinking-red" : ""
          }`}
        >
          🕒 Time Left: {formatTime(remainingTime)}
        </div>
      )}
  
      {/* Pop-up Modal */}
      <Modal show={showWarning} onHide={() => setShowWarning(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Session Ending Soon</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          Only 5 minutes are left in your session. Please wrap up your work.
        </Modal.Body>
        <Modal.Footer>
          <button
            className="btn btn-primary"
            onClick={() => setShowWarning(false)}
          >
            OK
          </button>
        </Modal.Footer>
      </Modal>
  
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


