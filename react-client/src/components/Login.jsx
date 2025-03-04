import React, { useState } from 'react';
import TutorChat from './TutorChat'; 
import Admin from './Admin'; 
import '../../styles/Login.css'; 

const Login = () => {
  const [role, setRole] = useState(null);
  const [studentId, setStudentId] = useState('');
  const [showStudentIdForm, setShowStudentIdForm] = useState(false);

  const handleRoleSelection = (selectedRole) => {
    if (selectedRole === 'student') {
      // Show the student ID input form
      setShowStudentIdForm(true);
      
    } else {
      // For other roles (e.g., admin), set the role directly
      setRole(selectedRole);
    }
  };

  const handleStudentIdSubmit = (e) => {
    e.preventDefault();
    // Validate the student ID
    if (/^\d{9}$/.test(studentId)) {
      // If valid, set the role to 'student'
      setRole('student');
    } else {
      alert('Please enter a valid 9-digit Student ID.');
    }
  };

  // Render the appropriate component based on the selected role
  if (role === 'student') {
    return <TutorChat studentId={studentId} />;
  } else if (role === 'admin') {
    return <Admin />;
  }

  // If no role is selected, show the login screen
  return (
    <div className="login-container">
      <h1>Welcome!</h1>
      <p>Please select your role:</p>
      <div className="button-container">
        <button
          className="button"
          onClick={() => handleRoleSelection('student')}
        >
          Student
        </button>
        <button
          className="button"
          onClick={() => handleRoleSelection('admin')}
        >
          Admin
        </button>
      </div>

      {/* Conditionally render the student ID input form if the student role is selected */}
      {showStudentIdForm && (
        <form onSubmit={handleStudentIdSubmit} className="student-id-form">
          <label htmlFor="studentId">Enter your Student ID (9 digits):</label>
          <input
            type="text"
            id="studentId"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            required
            maxLength={9}
            pattern="\d{9}"
            title="Please enter exactly 9 digits."
          />
          <button type="submit" className="button">
            Submit
          </button>
        </form>
      )}
    </div>
  );
};

export default Login;