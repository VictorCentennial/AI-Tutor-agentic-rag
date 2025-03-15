import { useState, useEffect } from "react";
import { Container, Modal, DropdownButton, Dropdown, Button } from "react-bootstrap";
import TutorStart from "./TutorStart";
import TutorInteraction from "./TutorInteraction";
import axios from "axios";
import "../App.css";
import PropTypes from 'prop-types';

function TutorChat({ studentId: propStudentId }) {
  const [isLoading, setIsLoading] = useState(false);
  const [aiMessages, setAiMessages] = useState([]);
  const [llmPrompt, setLlmPrompt] = useState("");
  const [isTutoringStarted, setIsTutoringStarted] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [nextState, setNextState] = useState("");
  const [remainingTime, setRemainingTime] = useState(0);
  const [showWarning, setShowWarning] = useState(false);
  const [showExtensionOptions, setShowExtensionOptions] = useState(false);
  const [selectedExtensionTime, setSelectedExtensionTime] = useState(0);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("");
  const [showSummaryScreen, setShowSummaryScreen] = useState(false);
  const [sessionSummary, setSessionSummary] = useState(null); // New state for summary
  const [savedTimestamp, setSavedTimestamp] = useState("");
  const [topicCode, setTopicCode] = useState("");

  // Get studentId from session storage if not provided as prop
  const studentId = propStudentId || sessionStorage.getItem('userId');

  useEffect(() => {
    if (isTutoringStarted && remainingTime >= 0) {
      const timer = setInterval(() => {
        setRemainingTime((prevTime) => {
          const newTime = prevTime - 1;
          if (newTime === 0) {
            handleSend("Time is up. We will summarize the session now.");
          }
          if (newTime === 300) {
            setShowWarning(true);
          }
          return newTime;
        });
      }, 1000);

      return () => clearInterval(timer);
    }
  }, [remainingTime, isTutoringStarted]);

  const handleStartTutoring = async (selectedFolder, selectedDuration, selectedTopic, currentWeek) => {
    try {
      setIsLoading(true);
      setSelectedFolder(selectedFolder);
      setTopicCode(selectedFolder.split('_')[0]);
      setSelectedTopic(selectedTopic);
      const response = await axios.post("api/start-tutoring", {
        student_id: studentId,
        folder_name: selectedFolder,
        duration: selectedDuration,
        topic: selectedTopic,
        current_week: currentWeek,
      });
      setIsLoading(false);

      const messages = response.data.messages;
      setThreadId(response.data.thread_id);
      setAiMessages(messages);

      const state = response.data.state;
      setLlmPrompt(state);
      setNextState(response.data.next_state);

      setIsTutoringStarted(true);
      setRemainingTime(selectedDuration * 60);


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
        student_id: studentId,
        student_response: userMessage,
        thread_id: threadId,
      });
      const { messages, state, next_state } = response.data;
      setIsLoading(false);
      setAiMessages(messages);
      setLlmPrompt(state);
      setNextState(next_state);

      if (next_state === null || next_state === "") {
        console.log("Saving session messages");
        await saveSessionMessages();
      }
    } catch (error) {
      console.error("Error continuing tutoring session:", error);
      setIsLoading(false);
    }
  };

  const saveSessionMessages = async () => {
    try {

      // Generate a custom timestamp in the format YYYYMMDD_HHMMSS
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0'); // Months are zero-based
      const day = String(now.getDate()).padStart(2, '0');
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');

      const timestamp = `${year}${month}${day}_${hours}${minutes}`;
      setSavedTimestamp(timestamp);

      console.log(`saved topic code: ${topicCode}`)

      const response = await axios.post("api/save-session", {
        thread_id: threadId,
        student_id: studentId,
        topic_code: topicCode, // Pass the extracted topic code
        time_stamp: timestamp // Pass the custom-formatted timestamp
      });

      console.log("Session messages saved successfully.");
      setSessionSummary(response.data.summary);
      setShowSummaryScreen(true);
    } catch (error) {
      console.error("Error saving session messages:", error);
    }
  };


  const extendSession = () => {
    if (selectedExtensionTime > 0) {
      setRemainingTime((prevTime) => prevTime + selectedExtensionTime * 60);
      setShowWarning(false);
      setShowExtensionOptions(false);
      axios.put("api/update-duration", {
        thread_id: threadId,
        duration_minutes: selectedExtensionTime,
      });
    }
  };

  const getDropdownTitle = () => {
    return selectedExtensionTime > 0
      ? `Extend by ${selectedExtensionTime} min`
      : "Extend Session";
  };

  const formatMessageContent = (message) => {
    const formattedContent = [];
    const lines = message.split("\n");

    lines.forEach((line, index) => {
      if (line.startsWith("**") && line.endsWith("**")) {
        // Heading
        formattedContent.push(
          <h3 key={`heading-${index}`} className="font-bold text-lg mt-4">
            {line.replace(/\*\*/g, "")}
          </h3>
        );
      } else if (line.startsWith("* ")) {
        // Bullet points
        formattedContent.push(
          <li key={`bullet-${index}`} className="ml-6 list-disc">
            {line.replace("* ", "")}
          </li>
        );
      } else if (line.trim()) {
        // Regular paragraph
        formattedContent.push(
          <p key={`paragraph-${index}`} className="mt-2">
            {line}
          </p>
        );
      }
    });

    return <div>{formattedContent}</div>;
  };
  const handleDownloadSessionHistory = async () => {
    try {

      // const topicCode = selectedFolder.split('_')[0];

      console.log(threadId)
      console.log(`download topic code: ${topicCode}`)
      const response = await axios.post(
        "api/download-session",
        {
          thread_id: threadId,
          student_id: studentId,
          topic_code: topicCode,
          time_stamp: savedTimestamp
        },
        { responseType: "blob" } // Ensure the response is treated as a file
      );

      const blob = new Blob([response.data], { type: response.headers["content-type"] || "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `session_${threadId}.txt`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error downloading session history:", error);
    }
  };




  return (
    <Container fluid className="mt-0 relative w-full p-0">
      {showSummaryScreen ? (
        <div className="summary-screen flex items-center justify-center h-screen bg-gray-100">
          <div className="p-6 bg-white  rounded-2xl w-2/3">
            <h1 className="text-2xl font-bold text-center mb-4">Summary of Session</h1>
            {sessionSummary ? (
              <div className="text-lg space-y-4">
                <p>
                  <strong>Subject:</strong> {sessionSummary.subject}
                </p>
                <p>
                  <strong>Start Time:</strong> {sessionSummary.start_time}
                </p>
                <p>
                  <strong>End Time:</strong> {sessionSummary.end_time}
                </p>
                <div>
                  <strong>Messages:</strong>
                  <div className="mt-2 space-y-2">
                    {sessionSummary.messages.length > 0 ? (
                      <div
                        className={`p-3 rounded-md ${sessionSummary.messages[sessionSummary.messages.length - 1].role === "AI"
                          ? "bg-blue-50 border border-blue-300"
                          : "bg-gray-50 border border-gray-300"
                          }`}
                      >
                        <strong>{sessionSummary.messages[sessionSummary.messages.length - 1].role}:</strong>{" "}
                        <div className="mt-2">
                          {formatMessageContent(sessionSummary.messages[sessionSummary.messages.length - 1].content)}
                        </div>
                      </div>
                    ) : (
                      <p>No messages to display.</p>
                    )}
                  </div>
                </div>
                <div className="text-center">
                  <Button
                    variant="dark"
                    onClick={handleDownloadSessionHistory}
                    className="mb-3 mt-3"
                  >
                    Download Session history
                  </Button>

                </div>
                <div className="text-center">
                  <Button
                    variant="dark"
                    onClick={() => window.location.reload()}
                    className="mb-3"
                  >
                    Start New Session
                  </Button>

                </div>
              </div>

            ) : (
              <p>No session summary available.</p>
            )}
          </div>
        </div>




      ) : (
        <>

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
              remainingTime={remainingTime}
              studentId={studentId}
            />
          )}
        </>

      )}

    </Container>
  );
}

// Add PropTypes validation
TutorChat.propTypes = {
  studentId: PropTypes.string
};

// Default props
TutorChat.defaultProps = {
  studentId: null
};

export default TutorChat;



