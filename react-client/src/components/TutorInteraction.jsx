import React, { useEffect, useRef, useState, useCallback } from "react";
import { Row, Col, Form, Button, Spinner } from "react-bootstrap";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { JsonView } from "react-json-view-lite";
import "react-json-view-lite/dist/index.css";
import MermaidDiagram from "./MermaidDiagram";
import PropTypes from "prop-types";
import "../../styles/TutorInteraction.css";

const debugMode = import.meta.env.VITE_DEBUG_MODE === "true";

// Header Component
const Header = () => (
  <header className="d-flex justify-content-between align-items-center py-1 border-bottom">
    <div className="d-flex align-items-center">
      <h3 className="text-primary mb-0 me-3">AI Tutor</h3>
    </div>
    <div className="d-flex align-items-center">
      <Button variant="outline-primary" className="me-2 custom-btn">View Session History</Button>
      <Button variant="outline-primary" className="custom-btn">View Progress</Button>
    </div>
  </header>
);

function TutorInteraction({
  aiMessages,
  llmPrompt,
  onSend,
  isLoading,
  nextState,
  selectedFolder,
  selectedTopic,
  remainingTime
}) {
  const [userMessage, setUserMessage] = useState("");
  const interactionBoxRef = useRef(null);
  const [graphData, setGraphData] = useState(null);

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

  const formatTime = (timeInSeconds) => {
    if (timeInSeconds <= 0) return "00:00";
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = timeInSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

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

  useEffect(() => {
    if (interactionBoxRef.current) {
      interactionBoxRef.current.scrollTop = interactionBoxRef.current.scrollHeight;
    }
  }, [aiMessages]);

  const handleSendMessage = useCallback(() => {
    if (userMessage.trim()) {
      onSend(userMessage);
      setUserMessage("");
    }
  }, [onSend, userMessage]);

  useEffect(() => {
    const handleKeyPress = (event) => {
      if (event.key === "Enter" && event.shiftKey) {
        handleSendMessage();
      }
    };

    document.addEventListener("keydown", handleKeyPress);
    return () => document.removeEventListener("keydown", handleKeyPress);
  }, [handleSendMessage]);

  return (
    <div className="flex-grow-1">
      <Header />
      <div className="d-flex justify-content-between align-items-center py-2 border-bottom">
        <div>
          <span className={remainingTime <= 300 && remainingTime !== 0 ? "blinking-red" : ""}>🕒 Time Left: </span> {formatTime(remainingTime)}
        </div>
        <div>
          <span className="fw-bold">Course:</span> {selectedFolder || "N/A"}
        </div>
        <div>
          <span className="fw-bold">Topic:</span> {selectedTopic || "All Topics"}
        </div>
      </div>
      <Row className="mt-2">
        <Col xs={12} className="mb-2">
          <div className="interaction-box" ref={interactionBoxRef}>
            {aiMessages.map((msg, index) => (
              <div key={index} className={`d-flex flex-column ${msg.role === "ai" ? "align-items-start" : "align-items-end"}`}>
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
      {/* Prompt Box
        {debugMode && graphData && (
        <Col xs={12} md={4} className="mb-3">
          <div className="prompt-box">
            
              <>
                <h5>LangGraph Workflow</h5>
                <MermaidDiagram definition={getMermaidDefinition(graphData)} />
                <h5 className="mt-4">State JSON (Debugging)</h5>
                <div
                  style={{
                    maxHeight: "400px",
                    overflowY: "auto",
                    fontFamily: "monospace",
                    fontSize: "12px",
                  }}
                >
                  <JsonView data={llmPrompt} />
                </div>
              </>      
          </div>
        </Col>
        )} */}
      <Row className="mt-1 input-container">
        <Col xs={8} md={10} className="mb-0">
          <Form.Control
            as="textarea"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder="Your message..."
            disabled={isLoading || !nextState || nextState === "student_answer_if_any_further_question" || nextState === "time_out_message"}
            style={{ borderRadius: "20px", padding: "5px" }}
          />
        </Col>
        <Col xs={10} md={2} className="text-center">
          <Button
            variant="success"
            onClick={handleSendMessage}
            className="w-100 custom-btn"
            disabled={isLoading || !nextState || nextState === "student_answer_if_any_further_question" || nextState === "time_out_message"}
          >
            Send
          </Button>
        </Col>
      </Row>
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
  remainingTime: PropTypes.number.isRequired
};

export default TutorInteraction;


