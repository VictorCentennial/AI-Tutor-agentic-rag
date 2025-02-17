import React from "react";
import "../../styles/Preloader.css";

function Preloader() {
  return (
    <div className="preloader-overlay">
  <div className="preloader-content">
    <h3>👋 Hello! I'm your AI Tutor for today.</h3>
    <br />
    <p>I'm preparing for our session. Here are a few tips to help you get the most out of it:</p>
    <p className="animated-text">1. 📚 Be ready for follow-up questions to deepen your understanding.</p>
    <p className="animated-text delay-1">2. ✍️ Focus on learning rather than seeking shortcuts.</p>
    <p className="animated-text delay-2">3. 👀 Stay on topic to keep our session productive.</p>
    <br />
    <div className="spinner-container">
      <div className="spinner" />
    </div>
    <p>✨ Preparing your session, please wait... ✨</p>
  </div>
  <div className="gif-container">
    <img src="../../../robo.gif" alt="Loading GIF" />
  </div>
</div>
  );
}

export default Preloader;