import React, { useState } from "react";
import axios from "axios";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';  // For GitHub-flavored markdown support

const AdminDashboard = () => {
  const [analysisType, setAnalysisType] = useState(null);
  const [filters, setFilters] = useState({});
  const [analysisResult, setAnalysisResult] = useState(null);

  const handleAnalysisType = (type) => {
    setAnalysisType(type);
    setFilters({});
    setAnalysisResult(null);
  };

  const fetchAnalysis = async () => {
    try {
      let endpoint = "";
      let payload = {};

      switch (analysisType) {
        case "general":
          endpoint = "/api/general-analysis";
          break;
        case "student":
          endpoint = "/api/student-analysis";
          payload = { student_id: filters.student_id };
          break;
        case "course":
          endpoint = "/api/course-analysis";
          payload = { course_code: filters.course_code };
          break;
        case "day":
          endpoint = "/api/day-analysis";
          payload = { date: filters.date };
          break;
        default:
          throw new Error("Invalid analysis type");
      }

      const response = await axios.post(endpoint, payload);
      setAnalysisResult(response.data);
      console.log(response.data)
    } catch (error) {
      console.error("Error fetching analysis:", error);
    }
  };

  // Styles
  const styles = {
    container: {
      backgroundColor: "#1E1E2F", // Dark blue background
      color: "#FFFFFF", // White text
      padding: "20px",
      borderRadius: "10px",
      fontFamily: "Arial, sans-serif",
    },
    header: {
      fontSize: "24px",
      fontWeight: "bold",
      marginBottom: "20px",
    },
    buttonContainer: {
      display: "flex",
      gap: "10px",
      marginBottom: "20px",
    },
    button: {
      backgroundColor: "#4CAF50", // Green
      color: "#FFFFFF",
      border: "none",
      padding: "10px 20px",
      borderRadius: "5px",
      cursor: "pointer",
      fontSize: "14px",
    },
    buttonHover: {
      backgroundColor: "#45a049", // Darker green on hover
    },
    input: {
      padding: "10px",
      borderRadius: "5px",
      border: "1px solid #ccc",
      marginBottom: "10px",
      width: "100%",
      maxWidth: "300px",
    },
    resultContainer: {
      backgroundColor: "#2D2D44", // Slightly lighter dark blue
      padding: "15px",
      borderRadius: "5px",
      marginTop: "20px",
    },
    resultText: {
      whiteSpace: "pre-wrap",
      wordWrap: "break-word",
      color: "black"
    },
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>Admin Dashboard</h1>

      <div style={styles.buttonContainer}>
        <button
          style={styles.button}
          onClick={() => handleAnalysisType("general")}
        >
          View General Model Analysis
        </button>
        <button
          style={styles.button}
          onClick={() => handleAnalysisType("student")}
        >
          View Student Specific Analysis
        </button>
        <button
          style={styles.button}
          onClick={() => handleAnalysisType("course")}
        >
          View Course Specific Analysis
        </button>
        <button
          style={styles.button}
          onClick={() => handleAnalysisType("day")}
        >
          View Day Specific Analysis
        </button>
      </div>

      {analysisType && (
        <div>
          <h2>{analysisType.replace(/-/g, " ").toUpperCase()} Analysis</h2>

          {/* Render filters based on analysis type */}
          {analysisType === "student" && (
            <div>
              <input
                style={styles.input}
                type="text"
                placeholder="Enter Student ID"
                value={filters.student_id || ""}
                onChange={(e) =>
                  setFilters({ ...filters, student_id: e.target.value })
                }
              />
            </div>
          )}

          {analysisType === "course" && (
            <div>
              <input
                style={styles.input}
                type="text"
                placeholder="Enter Course Code"
                value={filters.course_code || ""}
                onChange={(e) =>
                  setFilters({ ...filters, course_code: e.target.value })
                }
              />
            </div>
          )}

          {analysisType === "day" && (
            <div>
              <input
                style={styles.input}
                type="text"
                placeholder="Enter Date (YYYYMMDD)"
                value={filters.date || ""}
                onChange={(e) =>
                  setFilters({ ...filters, date: e.target.value })
                }
              />
            </div>
          )}

          <button style={styles.button} onClick={fetchAnalysis}>
            Fetch Analysis
          </button>
        </div>
      )}

      {analysisResult && (
        <div style={styles.resultContainer}>
          <h3>Analysis Results</h3>
          <div style={{
            ...styles.resultText,
            maxHeight: '500px',
            overflowY: 'auto',
            padding: '20px',
            backgroundColor: '#f8f9fa',  // Light background
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Style each markdown element
                h1: ({ node, ...props }) => <h1 style={{ color: '#2c3e50', marginBottom: '0.5em' }} {...props} />,
                h2: ({ node, ...props }) => <h2 style={{ color: '#2c3e50', marginBottom: '0.5em' }} {...props} />,
                h3: ({ node, ...props }) => <h3 style={{ color: '#2c3e50', marginBottom: '0.5em' }} {...props} />,
                p: ({ node, ...props }) => <p style={{ color: '#34495e', margin: '0.5em 0', lineHeight: '1.6' }} {...props} />,
                ul: ({ node, ...props }) => <ul style={{ margin: '0.5em 0', paddingLeft: '20px' }} {...props} />,
                li: ({ node, ...props }) => <li style={{ color: '#34495e', margin: '0.3em 0' }} {...props} />,
                strong: ({ node, ...props }) => <strong style={{ color: '#16a085' }} {...props} />,
                em: ({ node, ...props }) => <em style={{ color: '#2980b9' }} {...props} />
              }}
            >
              {analysisResult.summary}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;