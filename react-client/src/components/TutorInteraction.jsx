import React, { useState, useRef, useEffect, useCallback } from "react";
import { JsonView } from "react-json-view-lite";
import "react-json-view-lite/dist/index.css";
import MermaidDiagram from "./MermaidDiagram";
import PropTypes from "prop-types";
import "../../styles/TutorInteraction.css";
import axios from "axios";
import { Button, Row, Col, Form, Spinner } from "react-bootstrap";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const debugMode = import.meta.env.VITE_DEBUG_MODE === "true";

function TutorInteraction({
  aiMessages,
  llmPrompt,
  onSend,
  isLoading,
  nextState,
  selectedFolder,
  selectedTopic,
  remainingTime,
  studentId,
}) {
  const [userMessage, setUserMessage] = useState("");
  const interactionBoxRef = useRef(null);
  const [graphData, setGraphData] = useState(null);
  const [showProgress, setShowProgress] = useState(false); // State to manage progress visibility
  const [progressData, setProgressData] = useState(null); // State to store progress data

  // Fetch graph data on mount
  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        const response = await fetch("/api/get-graph");
        const data = await response.json();
        setGraphData(data.graph);
      } catch (error) {
        console.error("Error fetching graph data:", error);
      }
    };

    fetchGraphData();
  }, []);

  // Format time
  const formatTime = (timeInSeconds) => {
    if (timeInSeconds <= 0) return "00:00";
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = timeInSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  // Get Mermaid diagram definition
  const getMermaidDefinition = (graph) => {
    if (!graph) return "";
    let mermaidDef = "graph TD;\n";
    Object.entries(graph.nodes).forEach(([id, node]) => {
      mermaidDef += `${id}[\"${node.name}\"]\n`;
    });
    graph.edges.forEach((edge) => {
      mermaidDef += edge.conditional
        ? `${edge.source}-->|${edge.data}|${edge.target}\n`
        : `${edge.source}-->${edge.target}\n`;
    });
    return mermaidDef;
  };

  // Scroll to the bottom of the interaction box
  useEffect(() => {
    if (interactionBoxRef.current) {
      interactionBoxRef.current.scrollTop = interactionBoxRef.current.scrollHeight;
    }
  }, [aiMessages]);

  // Handle sending a message
  const handleSendMessage = useCallback(() => {
    if (userMessage.trim()) {
      onSend(userMessage);
      setUserMessage("");
    }
  }, [onSend, userMessage]);

  // Handle Enter key press for sending messages
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (event.key === "Enter" && event.shiftKey) {
        handleSendMessage();
      }
    };

    document.addEventListener("keydown", handleKeyPress);
    return () => document.removeEventListener("keydown", handleKeyPress);
  }, [handleSendMessage]);

  // Fetch student progress data
  const fetchStudentProgress = async () => {
    try {
      const endpoint = "/api/student-analysis";
      const payload = { student_id: studentId };
      const response = await axios.post(endpoint, payload);
      setProgressData(response.data); // Store the fetched data
      setShowProgress(true); // Show the progress section
    } catch (error) {
      console.error("Error fetching student progress:", error);
      alert("Failed to fetch progress data. Please try again.");
    }
  };

  // Format summary text (similar to AdminDashboard)
  const formatSummary = (summary) => {
    return summary
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // Bold
      .replace(/\*(.*?)\*/g, "<em>$1</em>") // Italic
      .replace(/\n/g, "<br />") // Line breaks
      .replace(/\*\s(.*?)\n/g, "<li>$1</li>"); // Convert bullet points to list items
  };

  // Header component with "View Progress" button
  const Header = () => (
    <header className="d-flex justify-content-between align-items-center py-3 border-bottom">
      <div className="d-flex align-items-center">
        <h3 className="text-white mb-0 me-3">AI Tutor</h3>
      </div>
      <div className="d-flex align-items-center">
        <Button variant="outline-light" className="me-2 custom-btn">
          View Session History
        </Button>
        <Button
          variant="outline-light"
          className="custom-btn"
          onClick={fetchStudentProgress} // Fetch progress on button click
        >
          View Progress
        </Button>
      </div>
    </header>
  );

  // Render progress section
  const renderProgressSection = () => {
    if (!showProgress || !progressData) return null;

    return (
      <div className="progress-section mt-3 p-3 border rounded">
        <h4>Student Progress</h4>
        <div className="card">
          <div className="card-header">
            <h5 className="card-title">Summary</h5>
          </div>
          <div className="card-content">
            <div
              dangerouslySetInnerHTML={{
                __html: formatSummary(progressData.summary),
              }}
            />
          </div>
        </div>
        <div className="visualizations mt-3">
          {Object.entries(progressData.visualizations).map(([key, src]) => (
            <div className="card mb-3" key={key}>
              <div className="card-header">
                <h5 className="card-title">
                  {key
                    .split("_")
                    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(" ")}
                </h5>
              </div>
              <div className="card-content">
                <div className="visualization-image">
                  <img
                    src={`http://localhost:5000/static/${src}`}
                    alt={key}
                    className="img-fluid"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="d-flex flex-column" style={{ height: "100vh", backgroundColor: "white" }}>
      <Header />
      <div className="d-flex justify-content-between align-items-center py-1">
        <div>
          <span className={remainingTime <= 300 && remainingTime !== 0 ? "blinking-red" : ""}>
            🕒 Time Left:{" "}
          </span>
          {formatTime(remainingTime)}
        </div>
        <div>
          <span className="fw-bold">Course:</span> {selectedFolder || "N/A"}
        </div>
        <div>
          <span className="fw-bold">Topic:</span> {selectedTopic || "All Topics"}
        </div>
      </div>
      <Row className="mt-2 flex-grow-1" style={{ overflowY: "auto" }}>
        <Col xs={12} className="mb-2 " style={{ backgroundColor: "white" }}>
          <div className="interaction-box " ref={interactionBoxRef}>
            {aiMessages.map((msg, index) => (
              <div
                key={index}
                className={`d-flex flex-column ${msg.role === "ai" ? "align-items-start" : "align-items-end"
                  }`}
              >
                <div className={`message-bubble ${msg.role === "ai" ? "ai-message" : "user-message"}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="d-flex justify-content-center mt-2">
                <Spinner animation="border" role="status" variant="primary" style={{ width: "2rem", height: "2rem", borderWidth: "0.2em" }} />
              </div>
            )}
          </div>
        </Col>
      </Row>
      {renderProgressSection()} {/* Render progress section */}
      <Row className="mt-1 input-container">
        <Col xs={8} md={10} className="mb-0">
          {nextState === "student_answer_if_any_further_question" ? (
            <div className="d-flex justify-content-center w-100">
              <Button
                variant="success"
                className="mx-2"
                onClick={() => onSend("Yes")}
                disabled={isLoading}
              >
                Yes
              </Button>
              <Button
                variant="danger"
                className="mx-2"
                onClick={() => onSend("No")}
                disabled={isLoading}
              >
                No
              </Button>
            </div>
          ) : (
            <Form.Control
              as="textarea"
              value={userMessage}
              onChange={(e) => setUserMessage(e.target.value)}
              placeholder="Your message..."
              disabled={isLoading || !nextState || nextState === "student_answer_if_any_further_question" || nextState === "time_out_message"}
              style={{ borderRadius: "20px", padding: "5px" }}
            />
          )}

          {/* <Form.Control
            as="textarea"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder="Your message..."
            disabled={isLoading || !nextState || nextState === "student_answer_if_any_further_question" || nextState === "time_out_message"}
            style={{ borderRadius: "20px", padding: "5px" }}
          /> */}
        </Col>
        {nextState != "student_answer_if_any_further_question" &&
          <Col xs={10} md={2} className="text-center">
            <Button
              variant="success"
              onClick={handleSendMessage}
              className="w-100 custom-btn"
              disabled={isLoading || !nextState || nextState === "student_answer_if_any_further_question" || nextState === "time_out_message"}
            >
              Send
            </Button>
          </Col>}
      </Row>

      {/* Add Debug Section at bottom */}
      {debugMode && (
        <Row className="mt-3 border-top pt-3">
          <Col xs={12}>
            <h5>State JSON (Debugging)</h5>
            <div
              style={{
                maxHeight: '200px',
                overflowY: 'auto',
                fontFamily: 'monospace',
                fontSize: '12px',
                backgroundColor: '#f8f9fa',
                padding: '10px',
                borderRadius: '4px',
                border: '1px solid #dee2e6'
              }}
            >
              <JsonView data={llmPrompt} />
            </div>
          </Col>
        </Row>
      )}
    </div>
  );
}

TutorInteraction.propTypes = {
  aiMessages: PropTypes.arrayOf(
    PropTypes.shape({
      role: PropTypes.string.isRequired,
      content: PropTypes.string.isRequired,
    })
  ).isRequired,
  llmPrompt: PropTypes.array.isRequired,
  onSend: PropTypes.func.isRequired,
  isLoading: PropTypes.bool.isRequired,
  nextState: PropTypes.string.isRequired,
  selectedFolder: PropTypes.string.isRequired,
  selectedTopic: PropTypes.string,
  remainingTime: PropTypes.number.isRequired,
  studentId: PropTypes.string.isRequired,
};

export default TutorInteraction;


