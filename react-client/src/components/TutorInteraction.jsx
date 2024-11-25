// TutorInteraction component for displaying user and AI interaction messages
import React, { useEffect, useRef } from "react";
import { Row, Col, Form, Button, Spinner } from "react-bootstrap";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm"; // Optional: GitHub-flavored markdown
import { JsonView } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css'; // Import styles
import MermaidDiagram from './MermaidDiagram';
// import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
// import { coy } from 'react-syntax-highlighter/dist/esm/styles/prism';
import PropTypes from 'prop-types';

TutorInteraction.propTypes = {
  aiMessages: PropTypes.arrayOf(PropTypes.shape({
    role: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired
  })).isRequired,
  llmPrompt: PropTypes.array.isRequired,
  onSend: PropTypes.func.isRequired,
  isLoading: PropTypes.bool.isRequired,
  nextState: PropTypes.string.isRequired
};

function TutorInteraction({ aiMessages, llmPrompt, onSend, isLoading, nextState }) {
  const [userMessage, setUserMessage] = React.useState("");
  const interactionBoxRef = useRef(null); // Reference to interaction box for smooth scrolling
  const [graphData, setGraphData] = React.useState(null);

  // Fetch graph data
  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        const response = await fetch('/api/get-graph');
        const data = await response.json();
        setGraphData(data.graph);

      } catch (error) {
        console.error('Error fetching graph data:', error);
      }
    };

    fetchGraphData();
  }, []);

  // Convert graph data to Mermaid syntax
  const getMermaidDefinition = (graph) => {
    let mermaidDef = 'graph TD;\n';

    // Add nodes
    Object.entries(graph.nodes).forEach(([id, node]) => {
      mermaidDef += `${id}["${node.name}"];\n`;
    });

    // Add edges
    graph.edges.forEach(edge => {
      if (edge.conditional) {
        // Conditional edges with labels
        mermaidDef += `${edge.source}-->|${edge.data}|${edge.target};\n`;
      } else {
        // Regular edges
        mermaidDef += `${edge.source}-->${edge.target};\n`;
      }
    });

    return mermaidDef;
  };


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
  }

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
            {isLoading && (
              <div className="d-flex justify-content-center mt-3">
                <Spinner
                  animation="border"
                  role="status"
                  variant="primary"
                  style={{
                    width: '2rem',
                    height: '2rem',
                    borderWidth: '0.2em'
                  }}
                />
              </div>
            )}
          </div>
        </Col>

        <Col xs={12} md={6} className="mb-3">
          <div className="prompt-box">
            <h5>LangGraph Workflow</h5>
            {graphData && (
              // <div
              //   className="mermaid-container"
              //   style={{
              //     background: 'white',
              //     padding: '20px',
              //     borderRadius: '8px',
              //     boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              //     marginBottom: '20px',
              //     maxHeight: '600px',
              //     overflowY: 'auto'
              //   }}
              // >
              //   <pre className="mermaid">
              //     {getMermaidDefinition(graphData)}
              //   </pre>
              // </div>
              <MermaidDiagram definition={getMermaidDefinition(graphData)} />
            )
            }
            {/* <h5>LLM Prompt (Debugging)</h5>
            <Form.Control
              as="textarea"
              value={typeof llmPrompt === 'object' ? JSON.stringify(llmPrompt, null, 2) : llmPrompt}
              readOnly
              placeholder="LLM Prompt will be shown here for debugging purposes."
            /> */}
            <h5>State JSON (Debugging)</h5>
            <div style={{ maxHeight: '400px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '12px' }}>
              <JsonView data={llmPrompt} />
            </div>
            {/* <div
              style={{
                backgroundColor: '#f8f9fa',
                padding: '15px',
                borderRadius: '5px',
                maxHeight: '400px',
                overflowY: 'auto',
                border: '1px solid #dee2e6',
                fontSize: '14px',
                lineHeight: '1.5',
              }}
            >
              <RenderJsonWithMarkdown data={llmPrompt} />
            </div> */}
          </div>
        </Col>
      </Row>

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
        </Col>
      </Row>

      <Row className="mt-4">
        <Col xs={12} className="text-center">
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

      <Row className="mt-4 input-container">
        <Col xs={12} md={10} className="mb-3">
          <Form.Control
            as="textarea"
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            placeholder="Your message..."
            disabled={isLoading || !nextState || nextState === "student_answer_if_any_further_question" || nextState === "time_out_message"}
          />
        </Col>
        <Col xs={12} md={2} className="text-center">
          <Button variant="success" onClick={handleSendMessage} className="w-100" disabled={isLoading || !nextState || nextState === "student_answer_if_any_further_question" || nextState === "time_out_message"}>
            Send
          </Button>
        </Col>
      </Row>
    </div>
  );
}

// function RenderJsonWithMarkdown({ data }) {
//   if (typeof data === 'string') {
//     // Simple check for markdown content
//     const isMarkdown = data.includes('*') || data.includes('#') || data.includes('- ') || data.includes('```');
//     if (isMarkdown) {
//       return (
//         <ReactMarkdown
//           // Use a custom renderer for code blocks
//           components={{
//             code({ node, inline, className, children, ...props }) {
//               const match = /language-(\w+)/.exec(className || '');
//               return !inline && match ? (
//                 <SyntaxHighlighter
//                   language={match[1]}
//                   style={coy}
//                   PreTag="div"
//                   {...props}
//                 >
//                   {String(children).replace(/\n$/, '')}
//                 </SyntaxHighlighter>
//               ) : (
//                 <code className={className} {...props}>
//                   {children}
//                 </code>
//               );
//             },
//           }}
//         >
//           {data}
//         </ReactMarkdown>
//       );
//     } else {
//       return <span>{data}</span>;
//     }
//   } else if (Array.isArray(data)) {
//     return (
//       <ul style={{ listStyleType: 'none', paddingLeft: '1em' }}>
//         {data.map((item, index) => (
//           <li key={index}>
//             <RenderJsonWithMarkdown data={item} />
//           </li>
//         ))}
//       </ul>
//     );
//   } else if (typeof data === 'object' && data !== null) {
//     return (
//       <div style={{ paddingLeft: '1em', borderLeft: '1px solid #ccc' }}>
//         {Object.entries(data).map(([key, value]) => (
//           <div key={key}>
//             <strong>{key}:</strong> <RenderJsonWithMarkdown data={value} />
//           </div>
//         ))}
//       </div>
//     );
//   } else {
//     return <span>{String(data)}</span>;
//   }
// }


export default TutorInteraction;
