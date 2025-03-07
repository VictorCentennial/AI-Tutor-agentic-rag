import React, { useState, useEffect } from "react";
import { Home, BarChart, BookOpen, ChevronDown, ChevronUp } from "lucide-react";
import axios from "axios";
import Modal from "./Modal";
import "../../styles/Admin.css";

const AdminDashboard = () => {
  const [currentView, setCurrentView] = useState("main");
  const [analysisType, setAnalysisType] = useState(null);
  const [filters, setFilters] = useState({});
  const [analysisResult, setAnalysisResult] = useState(null);
  const [statistics, setStatistics] = useState({
    totalSessions: 0,
    totalStudents: 0,
    totalCourses: 0,
  });

  // State for course management
  const [courses, setCourses] = useState([]); // List of courses
  const [expandedCourse, setExpandedCourse] = useState(null); // Track expanded course
  const [courseMaterial, setCourseMaterial] = useState({}); // Course material for each course
  const [isModalOpen, setIsModalOpen] = useState(false); // State to control modal visibility
  const [expandedWeeks, setExpandedWeeks] = useState({}); // Track expanded weeks separately
  

  // Fetch statistics when the component mounts
  useEffect(() => {
    const fetchStatistics = async () => {
      try {
        const response = await axios.get("/api/statistics");
        const mappedStatistics = {
          totalSessions: response.data.total_sessions,
          totalStudents: response.data.total_students,
          totalCourses: response.data.total_courses,
        };
        setStatistics(mappedStatistics);
      } catch (error) {
        console.error("Error fetching statistics:", error);
        alert("Failed to fetch statistics. Please try again.");
      }
    };

    fetchStatistics();
  }, []);

  const fetchCourses = async () => {
    try {
      const response = await axios.get("/api/get-courses");
      setCourses(response.data.courses);
      setExpandedCourse(null); // Reset expanded course
      setIsModalOpen(true); // Open the modal
    } catch (error) {
      console.error("Error fetching courses:", error);
      alert("Failed to fetch courses. Please try again.");
    }
  };
  

  const fetchCourseMaterial = async (courseName) => {
    try {
      const response = await axios.get("/api/get-course-material", {
        params: {
          course: courseName,
        },
      });
      console.log("Course Material Response:", response.data); // Debugging
  
      // Update state with the fetched material
      setCourseMaterial((prev) => ({
        ...prev,
        [courseName]: {
          material: response.data.material, // Ensure the response data is stored correctly
        },
      }));
      setExpandedCourse(courseName); // Expand the selected course
    } catch (error) {
      console.error("Error fetching course material:", error);
      alert("Failed to fetch course material. Please try again.");
    }
  };

  // Handle analysis type selection
  const handleAnalysisType = (type) => {
    setAnalysisType(type);
    setFilters({});
    setAnalysisResult(null);
    setCurrentView("analytics");
  };

  // Validate inputs for analysis
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

  // Fetch analysis data
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
      console.log(response.data);
    } catch (error) {
      console.error("Error fetching analysis:", error);
      alert("Failed to fetch analysis. Please try again.");
    }
  };

  // Format analysis summary
  const formatSummary = (summary) => {
    return summary
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/\n/g, "<br />")
      .replace(/\*\s(.*?)\n/g, "<li>$1</li>");
  };

  // Render analysis results
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
                  {key.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ")}
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

  // Navigation items
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
        { id: "day", label: "Daily Analysis" },
      ],
    },
  ];

  // Dropdown menu for analytics
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

  // Render analysis filters
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

  // Render home page
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

  const renderCourseManagement = () => {
    
    return (
      <div className="course-management">
        <div className="course-management-options">
          <div className="course-management-options-card" onClick={() => alert("Add a Course clicked")}>
            <h3>Add a Course</h3>
          </div>
          <div className="course-management-options-card" onClick={fetchCourses}>
            <h3>See existing courses</h3>
          </div>
          <div className="course-management-options-card" onClick={() => alert("Update Content clicked")}>
            <h3>Update Content of Existing Course</h3>
          </div>
          <div className="course-management-options-card" onClick={() => alert("Delete Course clicked")}>
            <h3>Delete a Course</h3>
          </div>
        </div>
    
        {/* Modal for displaying existing courses */}
        <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
          <div className="course-list" style={{ maxHeight: "70vh", overflowY: "auto" }}>
            <h2>Existing Courses</h2>
            {courses.map((course) => (
              <div key={course} className="course-item">
                <div
                  className="course-header"
                  onClick={() => {
                    if (expandedCourse === course) {
                      setExpandedCourse(null); // Collapse if already expanded
                    } else {
                      fetchCourseMaterial(course); // Fetch material if not already expanded
                    }
                  }}
                >
                  <h3>{course}</h3>
                  {expandedCourse === course ? <ChevronUp /> : <ChevronDown />}
                </div>
    
                {/* Render course material if expanded */}
                {expandedCourse === course && courseMaterial[course]?.material && (
                  <div className="course-material">
                    {Object.entries(courseMaterial[course].material).map(([week, files]) => (
                      <div key={week} className="week-item">
                        <div
                          className="week-header"
                          onClick={() => {
                            setExpandedWeeks((prev) => ({
                              ...prev,
                              [course]: {
                                ...(prev[course] || {}), // Ensure previous course object exists
                                [week]: !prev[course]?.[week],
                              },
                            }));
                            
                          }}
                        >
                          <h4>Week {week}</h4>
                          {expandedWeeks[course]?.[week] ? <ChevronUp /> : <ChevronDown />}
                        </div>
    
                        {/* Render files if week is expanded */}
                        {expandedWeeks[course]?.[week] && (
                          <div className="file-list">
                            {(Array.isArray(files) ? files : Object.values(files)).map((file, index) => (
                              <div key={index} className="file-item">
                                <p>{file}</p>
                              </div>
                            ))}
                          </div>
                        )}

                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Modal>
      </div>
    );
  };
  

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
              {currentView === "analytics"
                ? "Analytics Report"
                : currentView === "updateCourse"
                ? "Course Management"
                : analysisType
                ? `${analysisType.charAt(0).toUpperCase() + analysisType.slice(1)} Analysis`
                : "Welcome to Admin Dashboard"}
            </h2>
          </div>

          <div className="content-body">
            {currentView === "main" && renderHomePage()}
            {currentView === "analytics" && renderAnalysisFilters()}
            {currentView === "updateCourse" && renderCourseManagement()}
            {analysisResult && renderAnalysisResults()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;