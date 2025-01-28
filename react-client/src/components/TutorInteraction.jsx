import React, { useEffect, useRef } from "react";
import { Row, Col, Form, Button, Spinner } from "react-bootstrap";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { JsonView } from "react-json-view-lite";
import "react-json-view-lite/dist/index.css";
import MermaidDiagram from "./MermaidDiagram";
import PropTypes from "prop-types";

const debugMode = import.meta.env.VITE_DEBUG_MODE === "true";

// Header Component
const Header = ({ selectedFolder, selectedTopic }) => (
  <header className="d-flex justify-content-between align-items-center py-3 border-bottom">
    <h3 className="text-primary mb-0">AI Tutor System</h3>
    <div className="d-flex flex-column align-items-end">
      <div>
        <span className="fw-bold">Course:</span> {selectedFolder || "N/A"}
      </div>
      <div>
        <span className="fw-bold">Topic:</span> {selectedTopic || "All Topics"}
      </div>
    </div>
  </header>
);

Header.propTypes = {
  selectedFolder: PropTypes.string.isRequired,
  selectedTopic: PropTypes.string,
};

function TutorInteraction({
  aiMessages,
  llmPrompt,
  onSend,
  isLoading,
  nextState,
  selectedFolder,
  selectedTopic,
}) {
  const [userMessage, setUserMessage] = React.useState("");
  const interactionBoxRef = useRef(null);
  const [graphData, setGraphData] = React.useState(null);

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

  // Generate Mermaid syntax for graph
  const getMermaidDefinition = (graph) => {
    let mermaidDef = "graph TD;\n";
    Object.entries(graph.nodes).forEach(([id, node]) => {
      mermaidDef += `${id}["${node.name}"];\n`;
    });
    graph.edges.forEach((edge) => {
      mermaidDef += edge.conditional
        ? `${edge.source}-->|${edge.data}|${edge.target};\n`
        : `${edge.source}-->${edge.target};\n`;
    });
    return mermaidDef;
  };

  // Auto-scroll to the latest message
  useEffect(() => {
    if (interactionBoxRef.current) {
      interactionBoxRef.current.scrollTop =
        interactionBoxRef.current.scrollHeight;
    }
  }, [aiMessages]);

  // Handle sending a message
  const handleSendMessage = React.useCallback(() => {
    if (userMessage.trim()) {
      onSend(userMessage);
      setUserMessage("");
    }
  }, [onSend, userMessage]);

  // Listen for Shift + Enter to send the message
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
      {/* Header */}
      <Header selectedFolder={selectedFolder} selectedTopic={selectedTopic} />

      {/* Interaction and Prompt Sections */}
      <Row className="mt-4">
        {/* Interaction Box */}
        <Col xs={12} md={8} className="mb-3">
          <div className="interaction-box" ref={interactionBoxRef}>
            <h5>User and AI Interaction</h5>
            {aiMessages.map((msg, index) => (
              <div
                key={index}
                className={`message-bubble ${
                  msg.role === "ai" ? "ai-message" : "user-message"
                }`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            ))}
            {isLoading && (
              <div className="d-flex justify-content-center mt-3">
                <Spinner
                  animation="border"
                  role="status"
                  variant="primary"
                  style={{
                    width: "2rem",
                    height: "2rem",
                    borderWidth: "0.2em",
                  }}
                />
              </div>
            )}
          </div>
        </Col>

        {/* Prompt Box */}
        <Col xs={12} md={4} className="mb-3">
          <div className="prompt-box">
            <div className="session-info mb-4 mt-4">
              <div>
                <span className="fw-bold">Course:</span> {selectedFolder}
              </div>
              <div className="mt-3">
                <span className="fw-bold">Topic:</span>{" "}
                {selectedTopic || "All Topics"}
              </div>
            </div>
            {debugMode && graphData && (
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
            )}
          </div>
        </Col>
      </Row>

      {/* Footer Controls */}
      <Row className="mt-4">
        <Col xs={12} className="text-center">
          {!nextState && (
            <Button
              variant="primary"
              onClick={() => window.location.reload()}
              className="mb-3"
            >
              Start New Session
            </Button>
          )}
          {nextState === "student_answer_if_any_further_question" && (
            <div>
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
          )}
        </Col>
      </Row>

      {/* Input Area */}
      <Row className="mt-4 input-container">
        <Col xs={12} md={10} className="mb-3">
          <Form.Control
            as="textarea"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder="Your message..."
            disabled={
              isLoading ||
              !nextState ||
              nextState === "student_answer_if_any_further_question" ||
              nextState === "time_out_message"
            }
          />
        </Col>
        <Col xs={12} md={2} className="text-center">
          <Button
            variant="success"
            onClick={handleSendMessage}
            className="w-100"
            disabled={
              isLoading ||
              !nextState ||
              nextState === "student_answer_if_any_further_question" ||
              nextState === "time_out_message"
            }
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
};

export default TutorInteraction;
