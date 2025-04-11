import React, { useState, useEffect } from "react";
import { Card, Form, Button, Spinner, Row, Col, ListGroup } from "react-bootstrap";
import PropTypes from 'prop-types';
import axios from "axios";
import Preloader from "./Preloader";
import Modal from "./Modal";
import "../../styles/TutorInteraction.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useConfig } from "../utils/config";


function TutorStart({ onStartTutoring, isLoading }) {
  const [duration, setDuration] = useState(30);
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [folderLoading, setFolderLoading] = useState(true);
  const [isEmbeddingsLoading, setIsEmbeddingsLoading] = React.useState(false);
  const [currentWeek, setCurrentWeek] = useState(1);

  // States for the topic
  const [selectedTopic, setSelectedTopic] = useState("ALL");
  const [topics, setTopics] = useState([]);

  // States for conversation history
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [isConversationModalOpen, setIsConversationModalOpen] = useState(false);

  const config = useConfig();

  const semesterStartDate = config.SEMESTER_START_DATE;
  const totalWeeks = config.TOTAL_WEEKS || 14;
  const calculatedCurrentWeek = semesterStartDate ? Math.floor((new Date() - new Date(semesterStartDate)) / (7 * 24 * 60 * 60 * 1000)) + 1 : 1;
  const debugMode = Boolean(config.DEBUG_MODE);


  const weekAutoSet = !debugMode && semesterStartDate && calculatedCurrentWeek < totalWeeks;

  useEffect(() => {
    const fetchFolders = async () => {
      try {
        const response = await fetch('/api/get-folders');
        const data = await response.json();
        setFolders(data.folders);
        setSelectedFolder("");
        if (weekAutoSet) {
          setCurrentWeek(calculatedCurrentWeek);
        }
      } catch (error) {
        console.error('Error fetching folders:', error);
      } finally {
        setFolderLoading(false);
      }
    };

    fetchFolders();
  }, [calculatedCurrentWeek, weekAutoSet]);

  useEffect(() => {
    const fetchTopics = async () => {
      if (!selectedFolder) {
        setTopics([]);
        setSelectedTopic("ALL"); // Reset to "ALL" when folder changes
        return;
      }

      try {
        const response = await fetch(`/api/get-topics?folder=${selectedFolder}&current_week=${currentWeek}`);
        const data = await response.json();
        setTopics(data.topics);
        setSelectedTopic("ALL"); // Reset to "ALL" when topics update
      } catch (error) {
        console.error('Error fetching topics:', error);
      }
    };

    fetchTopics();
  }, [selectedFolder, currentWeek]);

  const handleStart = () => {
    onStartTutoring(selectedFolder, duration, selectedTopic, currentWeek);
  };

  const handleUpdateVectorStore = async () => {
    setIsEmbeddingsLoading(true);
    const response = await axios.post("api/update-vector-store", {
      folder_name: selectedFolder,
    });
    //handle response with popup window
    if (response.status === 200) {
      alert(response.data.message);
    } else {
      alert(response.data.error);
    }
    setIsEmbeddingsLoading(false);
  }

  const topicDisplay = (topic) => {
    const topic_split = topic.split("\\", 2);
    return `Week ${topic_split[0]} - ${topic_split[1]}`
  }

  // Function to fetch conversation history
  const fetchConversationHistory = async () => {
    setIsHistoryLoading(true);
    try {
      // Get the student ID from localStorage or another source
      const studentId = localStorage.getItem('userId') || sessionStorage.getItem('userId');

      if (!studentId) {
        alert('User ID not found. Please log in again.');
        setIsHistoryLoading(false);
        return;
      }

      const response = await axios.post('/api/get-student-chat-history', {
        student_id: studentId
      });

      if (response.status === 200 && response.data.conversations) {
        if (response.data.conversations.length === 0) {
          alert('No conversation history found for your account.');
        } else {
          setConversationHistory(response.data.conversations);
          setIsHistoryModalOpen(true);
        }
      } else {
        alert('Failed to fetch conversation history');
      }
    } catch (error) {
      console.error('Error fetching conversation history:', error);
      alert('Error fetching conversation history: ' + error.message);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  // Function to handle conversation selection
  const handleConversationSelect = (conversation) => {
    setSelectedConversation(conversation);
    setIsHistoryModalOpen(false);
    setIsConversationModalOpen(true);
  };

  // Format date for display
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="container mt-2">
      {/* Preloader Page */}
      {isLoading && <Preloader />}

      {/* Main Content */}
      {!isLoading && (
        <Card className="p-2">
          <Card.Title className="text-center mb-3">Start Your Tutoring Session</Card.Title>
          <Card.Body>
            <Form>
              <Form.Group className="mb-3">
                <Form.Label>Current Week</Form.Label>
                <Form.Control
                  type="number"
                  min="1"
                  max={totalWeeks}
                  step="1"
                  value={currentWeek}
                  onChange={(e) => setCurrentWeek(parseInt(e.target.value))}
                  disabled={weekAutoSet}
                />
              </Form.Group>
              <Row>
                <Col>
                  <Form.Group className="mb-2">
                    <Form.Label>Choose Course Material</Form.Label>
                    <Form.Select
                      value={selectedFolder}
                      onChange={(e) => setSelectedFolder(e.target.value)}
                      disabled={folderLoading}
                    >
                      <option value="">
                        {folderLoading ? "Loading courses..." : "Select a course"}
                      </option>
                      {!folderLoading && folders.map((folder) => (
                        <option key={folder} value={folder}>
                          {folder}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col>
                  <Form.Group className="mb-3">
                    <Form.Label>Select Topic (Optional)</Form.Label>
                    <Form.Select
                      value={selectedTopic}
                      onChange={(e) => setSelectedTopic(e.target.value)}
                      disabled={!selectedFolder}
                    >
                      {!selectedFolder ? (
                        <option value="">First select a course</option>
                      ) : (
                        <>
                          <option value="ALL">All topics</option>
                          {topics.map((topicName) => (
                            <option key={topicName} value={topicName}>
                              {topicDisplay(topicName)}
                            </option>
                          ))}
                        </>
                      )}
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>

              <div className="text-center mb-3">
                <Button
                  variant="dark"
                  onClick={handleUpdateVectorStore}
                  className="w-50"
                  disabled={isLoading || !selectedFolder || isEmbeddingsLoading} // Only enable if a folder is selected
                >
                  {isEmbeddingsLoading ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                        className="me-2"
                      />
                      Updating Course Material...
                    </>
                  ) : (
                    'Update Course Material'
                  )}
                </Button>
              </div>

              <Form.Group className="mb-3">
                <Form.Label>Session Duration (minutes)</Form.Label>
                <Form.Control
                  type="number"
                  min="15"
                  max="60"
                  step="15"
                  value={duration}
                  onChange={(e) => setDuration(parseInt(e.target.value))}
                />
              </Form.Group>

              <div className="text-center mb-3">
                <Button
                  variant="dark"
                  onClick={handleStart}
                  className="w-50"
                  disabled={isLoading || !selectedFolder || isEmbeddingsLoading}
                >
                  {isLoading ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                        className="me-2"
                      />
                      Loading...
                    </>
                  ) : (
                    'Start Tutoring'
                  )}
                </Button>
              </div>

              <div className="text-center">
                <Button
                  variant="outline-dark"
                  onClick={fetchConversationHistory}
                  className="w-50"
                  disabled={isHistoryLoading}
                >
                  {isHistoryLoading ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                        className="me-2"
                      />
                      Loading History...
                    </>
                  ) : (
                    'View Conversation History'
                  )}
                </Button>
              </div>
            </Form>
          </Card.Body>
        </Card>
      )}

      {/* History Modal */}
      <Modal isOpen={isHistoryModalOpen} onClose={() => setIsHistoryModalOpen(false)}>
        <div className="modal-header">
          <h3>Conversation History</h3>
        </div>
        {conversationHistory.length === 0 ? (
          <p style={{ color: '#333333', backgroundColor: '#ffffff', padding: '15px', borderRadius: '5px' }}>
            No conversation history found.
          </p>
        ) : (
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            <ListGroup>
              {conversationHistory.map((conversation, index) => (
                <ListGroup.Item
                  key={index}
                  action
                  onClick={() => handleConversationSelect(conversation)}
                  className="d-flex flex-sm-row flex-column justify-content-between align-items-start p-3"
                  style={{
                    margin: '8px 0',
                    borderRadius: '5px',
                    backgroundColor: '#f0f2f5',
                    border: '1px solid #d0d0d0',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <div className="w-100 mb-2 mb-sm-0">
                    <strong 
                      className="d-block text-truncate" 
                      style={{ color: '#1976d2', maxWidth: '90%' }}
                      title={conversation.subject || 'Unknown Subject'}
                    >
                      {conversation.subject || 'Unknown Subject'}
                    </strong>
                    <div className="text-muted small">
                      <span className="d-none d-sm-inline">
                        {formatDate(conversation.created_at)}
                      </span>
                      <span className="d-inline d-sm-none">
                        {new Date(conversation.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="text-muted small">
                      Messages: {conversation.message_count}
                    </div>
                  </div>
                  <Button 
                    variant="outline-primary" 
                    size="sm"
                    className="w-100 w-sm-auto mt-2 mt-sm-0"
                    style={{ minWidth: '80px' }}
                  >
                    View
                  </Button>
                </ListGroup.Item>
              ))}
            </ListGroup>
          </div>
        )}
      </Modal>

      {/* Conversation Detail Modal */}
      <Modal isOpen={isConversationModalOpen} onClose={() => setIsConversationModalOpen(false)}>
        {selectedConversation ? (
          <div>
            <div className="modal-header">
              <h3>Conversation Details</h3>
            </div>
            <div className="mb-3" >
              <strong>Subject:</strong> {selectedConversation.subject || 'Unknown Subject'}<br />
              <strong>Date:</strong> {formatDate(selectedConversation.created_at)}<br />
              <strong>Messages:</strong> {selectedConversation.message_count}<br />
            </div>
            <div
              className="conversation-messages"
            >
              {selectedConversation.messages && selectedConversation.messages.map((message, index) => (
                <div
                  key={index}

                  className={`d-flex flex-column ${message.role === 'student' ? 'align-items-end' : 'align-items-start'}`}
                >
                  <div className={`message-bubble ${message.role === 'student' ? 'user-message' : 'ai-message'}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}
                      components={{
                        code({ node, inline, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || '');
                          return !inline && match ? (
                            <SyntaxHighlighter
                              style={oneLight}
                              language={match[1]}
                              PreTag="div"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className={className} {...props}>
                              {children}
                            </code>
                          );
                        }
                      }}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p style={{ color: '#333333', backgroundColor: '#ffffff', padding: '15px', borderRadius: '5px' }}>
            No conversation selected.
          </p>
        )}
      </Modal>
    </div>
  );
}

TutorStart.propTypes = {
  onStartTutoring: PropTypes.func.isRequired,
  isLoading: PropTypes.bool.isRequired,
};

export default TutorStart;