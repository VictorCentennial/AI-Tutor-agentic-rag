// TutorStart component for selecting subject and topic to start tutoring
import React, { useState } from "react";
import { Row, Col, Form, Button } from "react-bootstrap";

function TutorStart({ onStartTutoring }) {
  const [subject, setSubject] = useState("Java");
  const [topic, setTopic] = useState("Polymorphism in Java");
  const [duration, setDuration] = useState(30);

  const subjects = ["Java", "C#", "Python"];
  const topics = {
    "Java": ["Polymorphism in Java", "Abstract classes", "Java Interfaces"],
    "C#": ["Inheritance in C#", "Delegates", "LINQ"],
    "Python": ["Python Decorators", "Classes in Python", "Generators"],
  };

  const handleStart = () => {
    onStartTutoring(subject, topic, duration); // Pass subject and topic to parent
  };

  return (
    <Row className="mt-4">
      <Col xs={12} md={6} className="mb-3">
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
      </Col>
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
        <Button variant="primary" onClick={handleStart} className="w-100">
          Start Tutoring
        </Button>
      </Col>
    </Row>
  );
}

export default TutorStart;
