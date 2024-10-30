// TutorInteraction component for displaying user and AI interaction messages
import React, { useEffect, useRef } from "react";
import { Row, Col, Form, Button } from "react-bootstrap";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm"; // Optional: GitHub-flavored markdown

function TutorInteraction({ aiMessages, llmPrompt, onSend }) {
  const [userMessage, setUserMessage] = React.useState("");
  const interactionBoxRef = useRef(null); // Reference to interaction box for smooth scrolling

  // Scroll to bottom when a new message is added
  useEffect(() => {
    if (interactionBoxRef.current) {
      interactionBoxRef.current.scrollTop = interactionBoxRef.current.scrollHeight;
    }
    console.log(`aiMessages: ${aiMessages}`);
  }, [aiMessages]);

  // For pressing Shift + Enter to send message
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (event.key === 'Enter' && event.shiftKey) {
        handleSendMessage();
      }
    };

    document.addEventListener('keydown', handleKeyPress);

    // Cleanup listener on component unmount
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [userMessage]);


  const handleSendMessage = () => {
    onSend(userMessage); // Pass the user's message to parent
    setUserMessage("");  // Clear the input after sending
  };

  return (
    <div className="flex-grow-1">
      <Row className="mt-4">
        <Col xs={12} md={6} className="mb-3">
          <div className="interaction-box" ref={interactionBoxRef}>
            <h5>User and AI Interaction</h5>
            {aiMessages.map((msg, index) => (
              <div
                key={index}
                className={`message-bubble ${msg.role === "ai" ? "ai-message" : "user-message"}`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {/* {msg.message} */}
                  {msg.content}
                </ReactMarkdown>
              </div>
            ))}
          </div>
        </Col>

        <Col xs={12} md={6} className="mb-3">
          <div className="prompt-box">
            <h5>LLM Prompt (Debugging)</h5>
            <Form.Control
              as="textarea"
              value={llmPrompt}
              readOnly
              placeholder="LLM Prompt will be shown here for debugging purposes."
            />
          </div>
        </Col>
      </Row>

      <Row className="mt-4 input-container">
        <Col xs={12} md={10} className="mb-3">
          <Form.Control
            as="textarea"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder="Your message..."
          />
        </Col>
        <Col xs={12} md={2} className="text-center">
          <Button variant="success" onClick={handleSendMessage} className="w-100">
            Send
          </Button>
        </Col>
      </Row>
    </div>
  );
}

export default TutorInteraction;
