// TutorStart component for selecting subject and topic to start tutoring
import { useState, useEffect } from "react";
import { Row, Col, Form, Button, Spinner } from "react-bootstrap";
import PropTypes from 'prop-types';

TutorStart.propTypes = {
  onStartTutoring: PropTypes.func.isRequired,
  isLoading: PropTypes.bool.isRequired,
};

function TutorStart({ onStartTutoring, isLoading }) {
  // const [subject, setSubject] = useState("Java");
  // const [topic, setTopic] = useState("Polymorphism in Java");
  const [duration, setDuration] = useState(30);
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState("");
  const [folderLoading, setFolderLoading] = useState(true);

  useEffect(() => {
    const fetchFolders = async () => {
      try {
        const response = await fetch('/api/get-folders');
        const data = await response.json();
        setFolders(data.folders);
        setSelectedFolder(""); // Reset selection when folders load
      } catch (error) {
        console.error('Error fetching folders:', error);
      } finally {
        setFolderLoading(false);
      }
    };

    fetchFolders();
  }, []);

  // const subjects = ["Java", "C#", "Python"];
  // const topics = {
  //   "Java": ["Polymorphism in Java", "Abstract classes", "Java Interfaces"],
  //   "C#": ["Inheritance in C#", "Delegates", "LINQ"],
  //   "Python": ["Python Decorators", "Classes in Python", "Generators"],
  // };

  const handleStart = () => {
    onStartTutoring(selectedFolder, duration);
  };

  return (
    <Row className="mt-4">
      <Col xs={12} md={6} className="mb-3">
        <Form.Group controlId="folder-select">
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

      {/* <Col xs={12} md={6} className="mb-3">
        <Form.Group controlId="subject-select">
          <Form.Label>Choose Subject</Form.Label>
          <Form.Control
            as="select"
            value={subject}
            onChange={(e) => {
              setSubject(e.target.value);
              setTopic(topics[e.target.value][0]);
            }}
          >
            {subjects.map((subject) => (
              <option key={subject} value={subject}>
                {subject}
              </option>
            ))}
          </Form.Control>
        </Form.Group>
      </Col> */}
      {/* 
      <Col xs={12} md={6} className="mb-3">
        <Form.Group controlId="topic-select">
          <Form.Label>Choose Topic</Form.Label>
          <Form.Control
            as="select"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          >
            {topics[subject].map((topic) => (
              <option key={topic} value={topic}>
                {topic}
              </option>
            ))}
          </Form.Control>
        </Form.Group>
      </Col> */}
      <Col xs={12} md={6} className="mb-3">
        <Form.Group controlId="duration-input">
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
      </Col>

      <Col className="text-center">
        <Button
          variant="primary"
          onClick={handleStart}
          className="w-100"
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
      </Col>
    </Row>
  );
}


export default TutorStart;
