import React, { useState, useEffect } from "react";
import { Card, Form, Button, Spinner, ProgressBar, Row, Col } from "react-bootstrap";
import PropTypes from 'prop-types';

function TutorStart({ onStartTutoring, isLoading }) {
  const [duration, setDuration] = useState(30);
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [folderLoading, setFolderLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(0);

  // States for the topic
  const [topic, setTopic] = useState("");

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
    let progressInterval;
    if (isLoading) {
      progressInterval = setInterval(() => {
        setLoadingProgress((prev) => {
          if (prev >= 100) {
            clearInterval(progressInterval);
            return 100;
          }
          return prev + 10;
        });
      }, 300);
    }
    return () => clearInterval(progressInterval);
  }, [isLoading]);

  const handleStart = () => {
    setLoadingProgress(0);
    onStartTutoring(selectedFolder, duration);
  };

  return (
    <div className="container mt-2">
      {/* Preloader Page */}
      {isLoading && (
        <div className="preloader-overlay">
          <div className="preloader-content">
            <h3>Hi !! I am your Tutor for today..</h3>
            <br />
            <p>While I am getting ready, please take a moment to review the following guidelines:</p>
            <p className="animated-text">1. Avoid asking irrelevant questions.</p>
            <p className="animated-text delay-1">2. AI Tutor will ask follow-up questions—please answer them to continue.</p>
            <p className="animated-text delay-2">3. Use the AI model for learning purposes, not for completing assignments.</p>
            <p className="animated-text delay-3">4. Enjoy the learning process!</p>
            <p className="animated-text delay-4">5. If you encounter any issues, try refreshing the page.</p>
            <p className="animated-text delay-5">6. Stay focused on the topic—this will help you get the most out of your session.</p>
            <p className="animated-text delay-6">7. Don&apos;t hesitate to ask for clarification if you don&apos;t understand something.</p>

            <br />
            <Spinner animation="border" role="status" />
            <p>Loading, please wait...</p>

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
                    <Form.Label>Select Topic</Form.Label>
                    <Form.Select
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                    >
                      <option value="">Select a Topic</option>
                      <option value="Math">Math</option>
                      <option value="Science">Science</option>
                      <option value="History">History</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
              </Row>

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
                  disabled={isLoading || !selectedFolder} // Only enable if a folder is selected
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

