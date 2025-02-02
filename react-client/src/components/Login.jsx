import React, { useState } from 'react';
import TutorChat from './TutorChat'; 
import Admin from './Admin'; 
import '../../styles/Login.css'; 

const Login = () => {
  const [role, setRole] = useState(null);

  const handleRoleSelection = (selectedRole) => {
    setRole(selectedRole);
  };

  // Render the appropriate component based on the selected role
  if (role === 'student') {
    return <TutorChat />;
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
    </div>
  );
};

export default Login;