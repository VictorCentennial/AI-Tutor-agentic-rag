import { useState, useEffect } from "react";
import { Container, Modal, DropdownButton, Dropdown } from "react-bootstrap";
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
  const [showExtensionOptions, setShowExtensionOptions] = useState(false); // New state to manage dropdown visibility
  const [selectedExtensionTime, setSelectedExtensionTime] = useState(0); // State for selected extension time

  const [selectedFolder, setSelectedFolder] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("");

  useEffect(() => {
    if (isTutoringStarted && remainingTime >= 0) {
      const timer = setInterval(() => {
        setRemainingTime((prevTime) => {
          const newTime = prevTime - 1;
          // When time reaches 0, trigger the timeout message
          if (newTime === 0) {
            handleSend("Time is up. We will summarize the session now.");
          }
          // Show warning pop-up when 5 minutes (300 seconds) are left
          if (newTime === 300) {
            setShowWarning(true);
          }
          return newTime;
        });
      }, 1000);

      return () => clearInterval(timer);
    }
  }, [remainingTime, isTutoringStarted]);

  const handleStartTutoring = async (selectedFolder, selectedDuration, selectedTopic) => {
    try {
      setIsLoading(true);
      setSelectedFolder(selectedFolder);
      setSelectedTopic(selectedTopic);
      const response = await axios.post("api/start-tutoring", {
        folder_name: selectedFolder,
        duration: selectedDuration,
        topic: selectedTopic,
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

  const handleSend = async (userMessage, AImessage = false) => {
    try {
      if (!AImessage) {
        setAiMessages([...aiMessages, { role: "User", content: userMessage }]);
      } else {
        setAiMessages([...aiMessages, { role: "AI", content: userMessage }]);
      }
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

      // Save messages if this is the end of the session
      if (next_state === null || next_state === "") {
        console.log("Saving session messages");
        await saveSessionMessages();
        console.log("Session messages saved");
      }
    } catch (error) {
      console.error("Error continuing tutoring session:", error);
      setIsLoading(false);
    }
  };

  const saveSessionMessages = async () => {
    await axios.post("api/save-session", {
      thread_id: threadId,
    });
  };

  const formatTime = (timeInSeconds) => {
    if (timeInSeconds <= 0) {
      return "00:00"; // When time is zero or negative
    }
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = timeInSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  // Modified extendSession function
  const extendSession = () => {
    if (selectedExtensionTime > 0) {
      setRemainingTime((prevTime) => prevTime + selectedExtensionTime * 60);
      setShowWarning(false);
      setShowExtensionOptions(false);
    }
  };

  // Helper function to get dropdown title
  const getDropdownTitle = () => {
    return selectedExtensionTime > 0 
      ? `Extend by ${selectedExtensionTime} min` 
      : "Extend Session";
  };

  return (
    <Container fluid className="mt-4 relative w-full">
      {isTutoringStarted && (
        <div className="absolute right-0 top-0 px-4 py-2 rounded-md text-right">
          <span>🕒 Time Left: </span>
          <span
            className={`${remainingTime <= 300 && remainingTime !== 0 ? "blinking-red" : ""}`}
          >
            {formatTime(remainingTime)}
          </span>
        </div>
      )}

      {/* Pop-up Modal */}
      <Modal show={showWarning} onHide={() => setShowWarning(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Session Ending Soon</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          Only 5 minutes are left in your session. Do you want to extend it?
        </Modal.Body>
        <Modal.Footer>
          <button className="btn btn-secondary" onClick={() => setShowWarning(false)}>
            Cancel
          </button>

          {/* Modified DropdownButton to show selection in title */}
          <DropdownButton
            variant="primary"
            title={getDropdownTitle()}
            onSelect={(time) => setSelectedExtensionTime(Number(time))}
            show={showExtensionOptions}
            onToggle={() => setShowExtensionOptions(!showExtensionOptions)}
          >
            <Dropdown.Item eventKey="5">Extend by 5 min</Dropdown.Item>
            <Dropdown.Item eventKey="15">Extend by 15 min</Dropdown.Item>
            <Dropdown.Item eventKey="30">Extend by 30 min</Dropdown.Item>
          </DropdownButton>

          {/* Button to apply extension */}
          {selectedExtensionTime > 0 && (
            <button className="btn btn-primary" onClick={extendSession}>
              Apply Extension
            </button>
          )}
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
          selectedFolder={selectedFolder}
          selectedTopic={selectedTopic}
          threadId={threadId}
        />
      )}
    </Container>
  );
}

export default TutorChat;


