import React, { useState, useEffect } from "react";
import { Card, Form, Button, Spinner, Row, Col } from "react-bootstrap";
import PropTypes from 'prop-types';
import axios from "axios";

function TutorStart({ onStartTutoring, isLoading }) {
  const [duration, setDuration] = useState(30);
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [folderLoading, setFolderLoading] = useState(true);
  const [isEmbeddingsLoading, setIsEmbeddingsLoading] = React.useState(false);

  // States for the topic
  const [selectedTopic, setSelectedTopic] = useState("");
  const [topics, setTopics] = useState([]);

  useEffect(() => {
    const fetchFolders = async () => {
      try {
        const response = await fetch('/api/get-folders');
        const data = await response.json();
        setFolders(data.folders);
        setSelectedFolder("");
      } catch (error) {
        console.error('Error fetching folders:', error);
      } finally {
        setFolderLoading(false);
      }
    };

    fetchFolders();
  }, []);

  useEffect(() => {
    const fetchTopics = async () => {
      if (!selectedFolder) {
        setTopics([]);
        return;
      }

      try {
        const response = await fetch(`/api/get-topics?folder=${selectedFolder}`);
        const data = await response.json();
        setTopics(data.topics);
        setSelectedTopic(""); // Reset selected topic
      } catch (error) {
        console.error('Error fetching topics:', error);
      }
    };

    fetchTopics();
  }, [selectedFolder]);

  const handleStart = () => {
    onStartTutoring(selectedFolder, duration, selectedTopic);
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


  return (
<div className="container mt-2">
  {/* Preloader Page */}
  {isLoading && (
    <div className="preloader-overlay">
      <div className="preloader-content">
        <h3>👋 Hi there! I'm your AI Tutor for today...</h3>
        <br />
        <p>I'm suiting up and gathering my AI superpowers 🦸‍♀️. Meanwhile, here are a few fun tips to prep for our session:</p>
        <p className="animated-text">1. 🤔 Please avoid asking questions like, "What's the meaning of life?"</p>
        <p className="animated-text delay-1">2. 📚 Be ready for follow-up questions</p>
        <p className="animated-text delay-2">3. ✍️ Use me for learning, not for shortcuts (your brain will thank you!).</p>
        <p className="animated-text delay-3">4. 👀 Stay on topic—it helps us stay sharp and focused.</p>
        <p className="animated-text delay-4">5. 🤷‍♀️ If you're lost, just ask! I don't judge (I can't, I'm an AI).</p>
        <br />
        <div className="spinner-container">
          <div className="spinner" />
        </div>
        <p>✨ Prepping your session, hang tight! ✨</p>
      </div>
    </div>
  )}


      {/* Main Content */}
      {!isLoading && (
        <Card className="p-2">
          <Card.Title className="text-center mb-3">Start Your Tutoring Session</Card.Title>
          <Card.Body>
            <Form>
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
                      <option value="">
                        {!selectedFolder
                          ? "First select a course"
                          : "All topics"}
                      </option>
                      {topics.map((topicName) => (
                        <option key={topicName} value={topicName}>
                          {topicName}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>

              <div className="text-center">
                <Button
                  variant="primary"
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

              <div className="text-center">
                <Button
                  variant="primary"
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
            </Form>
          </Card.Body>
        </Card>
      )}
    </div>
  );
}

TutorStart.propTypes = {
  onStartTutoring: PropTypes.func.isRequired,
  isLoading: PropTypes.bool.isRequired,
};

export default TutorStart;

