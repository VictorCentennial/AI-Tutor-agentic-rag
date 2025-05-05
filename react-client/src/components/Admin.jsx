import React, { useState, useEffect } from "react";
import { Home, BarChart, BookOpen, ChevronDown, ChevronUp, Trash, Edit } from "lucide-react";
import axios from "axios";
import Modal from "./Modal";
import "../../styles/Admin.css";

const AdminDashboard = () => {
  const [currentView, setCurrentView] = useState("main");
  const [analysisType, setAnalysisType] = useState(null);
  const [filters, setFilters] = useState({});
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isFetching, setIsFetching] = useState(false);
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
  const [isAddCourseModalOpen, setIsAddCourseModalOpen] = useState(false);
  const [courseCode, setCourseCode] = useState("");
  const [courseName, setCourseName] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  
  // New state for dropdown options
  const [studentIdOptions, setStudentIdOptions] = useState([]);
  const [courseCodeOptions, setCourseCodeOptions] = useState([]);

  // Fetch student IDs for dropdown
  const fetchStudentIds = async () => {
    try {
      const response = await axios.get("/api/get-all-students-id");
      // Student IDs come as a simple array
      if (response.data && Array.isArray(response.data)) {
        setStudentIdOptions(response.data);
      } else {
        console.error("Unexpected response format for student IDs:", response.data);
        setStudentIdOptions([]); // Set to empty array as fallback
      }
    } catch (error) {
      console.error("Error fetching student IDs:", error);
      setStudentIdOptions([]); // Set to empty array on error
    }
  };

  // Fetch course codes for dropdown
  const fetchCourseCodes = async () => {
    try {
      const response = await axios.get("/api/get-folders");
      // Response should have a folders array
      if (response.data && Array.isArray(response.data.folders)) {
        // Extract course codes (first part before underscore)
        const courseCodes = response.data.folders
          .map(folder => {
            const parts = folder.split("_");
            return parts.length > 0 ? parts[0] : "";
          })
          .filter(code => code !== "") // Remove empty codes
          .filter((code, index, self) => self.indexOf(code) === index); // Remove duplicates
        setCourseCodeOptions(courseCodes);
      } else {
        console.error("Unexpected response format for folders:", response.data);
        setCourseCodeOptions([]); // Set to empty array as fallback
      }
    } catch (error) {
      console.error("Error fetching course codes:", error);
      setCourseCodeOptions([]); // Set to empty array on error
    }
  };

  // Fetch dropdown options when analysis type changes
  useEffect(() => {
    if (analysisType === "student") {
      fetchStudentIds();
    } else if (analysisType === "course") {
      fetchCourseCodes();
    }
  }, [analysisType]);

  const handleAddCourse = async () => {
    if (!courseCode || !courseName) {
      alert("Please enter both course code and course name.");
      return;
    }
  
    try {
      const response = await axios.post("/api/add-course", {
        course_code: courseCode,
        course_name: courseName,
      });
      alert(response.data.message);
      setIsAddCourseModalOpen(false);
      setCourseCode("");
      setCourseName("");
    } catch (error) {
      console.error("Error adding course:", error);
      alert("Failed to add course. Please try again.");
    }
  };
  
  useEffect(() => {
    if (currentView !== "analytics") {
      setAnalysisResult(null); // Clear results when leaving analytics view
    }
  }, [currentView]);

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
      //setExpandedCourse(null);
      //setExpandedWeeks({}); // Reset expanded weeks when fetching courses
      if (expandedCourse) {
        fetchCourseMaterial(expandedCourse);
      }
      setIsModalOpen(true);
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
      alert("Please select a Student ID.");
      return false;
    }
    if (analysisType === "course" && !filters.course_code) {
      alert("Please select a Course Code.");
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
      setIsFetching(true);
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
    } finally {
      setIsFetching(false);
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
                    src={`/api/static/${src}`}
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
        <div className="filter-select-container">
          <label 
            htmlFor="student-select" 
            style={{ marginRight: "10px", display: "inline-block", minWidth: "120px" }}
          >
            Select Student ID:
          </label>
          <select
            id="student-select"
            value={filters.student_id || ""}
            onChange={(e) => setFilters({ ...filters, student_id: e.target.value })}
            className="filter-select"
            style={{ minWidth: "200px" }}
          >
            <option value="">-- Select Student ID --</option>
            {studentIdOptions.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>
      )}
      {analysisType === "course" && (
        <div className="filter-select-container">
          <label 
            htmlFor="course-select"
            style={{ marginRight: "10px", display: "inline-block", minWidth: "120px" }}
          >
            Select Course Code:
          </label>
          <select
            id="course-select"
            value={filters.course_code || ""}
            onChange={(e) => setFilters({ ...filters, course_code: e.target.value })}
            className="filter-select"
            style={{ minWidth: "200px" }}
          >
            <option value="">-- Select Course Code --</option>
            {courseCodeOptions.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </div>
      )}
      {analysisType === "day" && (
        <div className="filter-select-container">
          <label 
            htmlFor="date-input"
            style={{ marginRight: "10px", display: "inline-block", minWidth: "120px" }}
          >
            Select Date:
          </label>
          <input
            id="date-input"
            type="date"
            value={filters.formattedDate || ""}
            onChange={(e) => {
              // Convert from YYYY-MM-DD to YYYYMMDD format
              const selectedDate = e.target.value;
              const formattedForAPI = selectedDate ? selectedDate.replace(/-/g, "") : "";
              setFilters({ 
                ...filters, 
                date: formattedForAPI, 
                formattedDate: selectedDate 
              });
            }}
            className="filter-input"
            style={{ minWidth: "200px" }}
          />
        </div>
      )}
      {analysisType && (
        <button 
          className="fetch-button" 
          onClick={fetchAnalysis} 
          disabled={isFetching}
          style={{ marginTop: "15px" }}
        >
          {isFetching ? "Fetching..." : "Fetch Analysis"}
        </button>
      )}
      {isFetching && (
        <div className="loading-indicator">
          <div className="loading-spinner"></div>
        </div>
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
    const handleRename = async (type, oldPath, newName) => {
      if (!newName) {
        alert("Please enter a new name.");
        return;
      }
  
      try {
        const response = await axios.post("/api/rename-item", {
          type,
          old_path: oldPath,
          new_name: newName,
        });
        alert(response.data.message);
        fetchCourses(); // Refresh the course list
      } catch (error) {
        console.error("Error renaming item:", error);
        alert("Failed to rename item. Please try again.");
      }
    };
  
    const handleDelete = async (type, path) => {
      try {
        const response = await axios.post("/api/delete-item", {
          type,
          path,
        });
        alert(response.data.message);
        fetchCourses(); // Refresh the course list
      } catch (error) {
        console.error("Error deleting item:", error);
        alert("Failed to delete item. Please try again.");
      }
    };
  
    const handleUploadFile = async (courseName, weekNumber, file) => {
      if (!file) return;
      
      try {
        setIsUploading(true); // Show loading overlay
        
        const formData = new FormData();
        formData.append("course_name", courseName);
        formData.append("week_number", weekNumber);
        formData.append("file", file);

        const response = await axios.post("api/upload-file", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
        
        alert(response.data.message);
        fetchCourses(); // Refresh the course list
      } catch (error) {
        console.error("Error uploading file:", error);
        alert("Failed to upload file. Please try again.");
      } finally {
        setIsUploading(false); // Hide loading overlay when done
      }
    };
  
    return (
      <div className="course-management">
        <div className="course-management-options">
          <div className="course-management-options-card" onClick={() => setIsAddCourseModalOpen(true)}>
            <h3>Add a Course</h3>
          </div>
          <div className="course-management-options-card" onClick={fetchCourses}>
            <h3>See existing courses</h3>
          </div>
          <div className="course-management-options-card" onClick={fetchCourses}>
            <h3>Update Content of Existing Course</h3>
          </div>
        </div>
  
        {/* Modal for adding a course */}
        <Modal isOpen={isAddCourseModalOpen} onClose={() => setIsAddCourseModalOpen(false)}>
          <div className="add-course-modal">
            <h2>Add a New Course</h2>
            <input
              type="text"
              placeholder="Enter Course Code"
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value)}
            />
            <input
              type="text"
              placeholder="Enter Course Name"
              value={courseName}
              onChange={(e) => setCourseName(e.target.value)}
            />
            <button onClick={handleAddCourse}>Create Course</button>
          </div>
        </Modal>
  
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
                  <div className="icon-container">
                    {/* <Edit
                      className="icon-button"
                      onClick={(e) => {
                        e.stopPropagation(); // Prevent the course from collapsing/expanding
                        handleRename("course", course, prompt("Enter new course name"));
                      }}
                    /> */}
                    <Trash
                      className="icon-button"
                      onClick={(e) => {
                        e.stopPropagation(); // Prevent the course from collapsing/expanding
                        handleDelete("course", course);
                      }}
                    />
                  </div>
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
                                ...(prev[course] || {}),
                                [week]: !prev[course]?.[week],
                              },
                            }));
                          }}
                        >
                          <h4>Week {week}</h4>
                          {expandedWeeks[course]?.[week] ? <ChevronUp /> : <ChevronDown />}
                          <div className="icon-container">
                            {/* <Edit
                              className="icon-button"
                              onClick={(e) => {
                                e.stopPropagation(); // Prevent the week from collapsing/expanding
                                handleRename("week", `${course}/${week}`, prompt("Enter new week number"));
                              }}
                            /> */}
                            <Trash
                              className="icon-button"
                              onClick={(e) => {
                                e.stopPropagation(); // Prevent the week from collapsing/expanding
                                handleDelete("week", `${course}/${week}`);
                              }}
                            />
                          </div>
                        </div>
  
                        {expandedWeeks[course]?.[week] && (
                          <div className="file-list">
                            {files.map((file, index) => {
                              const fileName = decodeURIComponent(file.split("/").pop()); // Extract filename from URL
                              return (
                                <div key={index} className="file-item">
                                  {fileName}
                                  {/* <a href={file} target="_blank" rel="noopener noreferrer">
                                    {fileName}
                                  </a> */}
                                  <div className="icon-container">
                                    {/* <Edit
                                      className="icon-button"
                                      onClick={(e) => {
                                        e.stopPropagation(); // Prevent the file list from collapsing/expanding
                                        handleRename("file", `${course}/${week}/${fileName}`, prompt("Enter new file name"));
                                      }}
                                    /> */}
                                    <Trash
                                      className="icon-button"
                                      onClick={(e) => {
                                        e.stopPropagation(); // Prevent the file list from collapsing/expanding
                                        handleDelete("file", `${course}/${week}/${fileName}`);
                                      }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                            <input
                              type="file"
                              onChange={(e) => handleUploadFile(course, week, e.target.files[0])}
                            />
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
            {currentView === "analytics" && analysisResult && renderAnalysisResults()}
          </div>
        </div>
      </div>
    {isUploading && (
      <div className="loading-overlay">
        <div className="loading-spinner"></div>
        <div className="loading-text">Uploading File...</div>
      </div>
    )}
    </div>
  );
};

export default AdminDashboard;