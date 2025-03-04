import React, { useState, useEffect } from "react";
import { Home, BarChart, BookOpen } from "lucide-react";
import axios from "axios";
import "../../styles/Admin.css";

const AdminDashboard = () => {
  const [currentView, setCurrentView] = useState("main");
  const [analysisType, setAnalysisType] = useState(null);
  const [filters, setFilters] = useState({});
  const [analysisResult, setAnalysisResult] = useState(null);
  const [statistics, setStatistics] = useState({
    totalSessions: 0,
    totalStudents: 0,
    totalCourses: 0
  });

  // Fetch statistics when the component mounts
  useEffect(() => {
    const fetchStatistics = async () => {
      try {
        const response = await axios.get("/api/statistics");
        // Map the backend response to the expected structure
        const mappedStatistics = {
          totalSessions: response.data.total_sessions,
          totalStudents: response.data.total_students,
          totalCourses: response.data.total_courses
        };
        setStatistics(mappedStatistics); // Set the mapped statistics
      } catch (error) {
        console.error("Error fetching statistics:", error);
        alert("Failed to fetch statistics. Please try again.");
      }
    };

    fetchStatistics();
  }, []);

  // Rest of your code remains unchanged...
  const handleAnalysisType = (type) => {
    setAnalysisType(type);
    setFilters({});
    setAnalysisResult(null);
    setCurrentView("analytics");
  };

  const validateInputs = () => {
    if (analysisType === "student" && !filters.student_id) {
      alert("Please enter a valid Student ID.");
      return false;
    }
    if (analysisType === "course" && !filters.course_code) {
      alert("Please enter a valid Course Code.");
      return false;
    }
    if (analysisType === "day" && !/^\d{8}$/.test(filters.date)) {
      alert("Please enter a valid date in YYYYMMDD format.");
      return false;
    }
    return true;
  };

  const fetchAnalysis = async () => {
    if (!validateInputs()) return;

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
      alert("Failed to fetch analysis. Please try again.");
    }
  };

  const formatSummary = (summary) => {
    return summary
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br />')
      .replace(/\*\s(.*?)\n/g, '<li>$1</li>');
  };

  const renderAnalysisResults = () => (
    analysisResult && (
      <div className="analysis-results">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Analysis Summary</h3>
          </div>
          <div className="card-content">
            <div dangerouslySetInnerHTML={{ __html: formatSummary(analysisResult.summary) }} />
          </div>
        </div>
        <div className="visualizations">
          {Object.entries(analysisResult.visualizations).map(([key, src]) => (
            <div className="card" key={key}>
              <div className="card-header">
                <h3 className="card-title">
                  {key.split('_').map(word =>
                    word.charAt(0).toUpperCase() + word.slice(1)
                  ).join(' ')}
                </h3>
              </div>
              <div className="card-content">
                <div className="visualization-image">
                  <img
                    src={`http://localhost:5000/static/${src}`}
                    alt={key}
                    className="image"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  );

  const navItems = [
    { id: "main", label: "Dashboard", icon: Home },
    { id: "updateCourse", label: "Courses", icon: BookOpen },
    {
      id: "analytics",
      label: "Analytics",
      icon: BarChart,
      subItems: [
        { id: "general", label: "General Model Analysis" },
        { id: "student", label: "Student Analysis" },
        { id: "course", label: "Course Analysis" },
        { id: "day", label: "Daily Analysis" }
      ]
    }
  ];

  const DropdownMenu = ({ subItems, handleAnalysisType }) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
      <div className="dropdown">
        <button className="dropdown-toggle" onClick={() => setIsOpen(!isOpen)}>
          Analytics
        </button>
        {isOpen && (
          <div className="dropdown-menu">
            {subItems.map((item) => (
              <button
                key={item.id}
                className="dropdown-item"
                onClick={() => {
                  handleAnalysisType(item.id);
                  setIsOpen(false);
                }}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderAnalysisFilters = () => (
    <div className="filters">
      {analysisType === "student" && (
        <input
          type="text"
          placeholder="Enter Student ID"
          value={filters.student_id || ""}
          onChange={(e) => setFilters({ ...filters, student_id: e.target.value })}
          className="filter-input"
        />
      )}
      {analysisType === "course" && (
        <input
          type="text"
          placeholder="Enter Course Code"
          value={filters.course_code || ""}
          onChange={(e) => setFilters({ ...filters, course_code: e.target.value })}
          className="filter-input"
        />
      )}
      {analysisType === "day" && (
        <input
          type="text"
          placeholder="Enter Date (YYYYMMDD)"
          value={filters.date || ""}
          onChange={(e) => setFilters({ ...filters, date: e.target.value })}
          className="filter-input"
        />
      )}
      {analysisType && (
        <button className="fetch-button" onClick={fetchAnalysis}>
          Fetch Analysis
        </button>
      )}
    </div>
  );

  const renderHomePage = () => (
    <div className="home-page">
      <div className="statistics">
        <div className="statistic-card">
          <h3>Total Sessions</h3>
          <p>{statistics.totalSessions}</p>
        </div>
        <div className="statistic-card">
          <h3>Total Students</h3>
          <p>{statistics.totalStudents}</p>
        </div>
        <div className="statistic-card">
          <h3>Total Courses</h3>
          <p>{statistics.totalCourses}</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <div className="sidebar-content">
          <h1 className="sidebar-title">Admin Dashboard</h1>
          <nav className="nav">
            {navItems.map(({ id, label, icon: Icon, subItems }) => (
              <div key={id}>
                {subItems ? (
                  <DropdownMenu subItems={subItems} handleAnalysisType={handleAnalysisType} />
                ) : (
                  <button
                    className={`nav-button ${currentView === id ? "active" : ""}`}
                    onClick={() => setCurrentView(id)}
                  >
                    <Icon className="nav-icon" />
                    {label}
                  </button>
                )}
              </div>
            ))}
          </nav>
        </div>
      </div>

      <div className="main-content">
        <div className="content">
          <div className="header">
            <h2 className="header-title">
              {currentView === "analytics" ? "Analytics Report" :
                currentView === "updateCourse" ? "Course Management" :
                  analysisType ? `${analysisType.charAt(0).toUpperCase() + analysisType.slice(1)} Analysis` :
                    "Welcome to Admin Dashboard"}
            </h2>
          </div>

          <div className="content-body">
            {currentView === "main" && renderHomePage()}
            {currentView === "analytics" && renderAnalysisFilters()}
            {analysisResult && renderAnalysisResults()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;