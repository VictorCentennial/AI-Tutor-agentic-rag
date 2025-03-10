import React from "react";
import "../../styles/modal.css";

const Modal = ({ isOpen, onClose, children }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{
        backgroundColor: '#ffffff',
        padding: '50px',
        borderRadius: '5px',
        border: '1px solid #d0d0d0',
        color: '#333333'
      }}>
        <button className="modal-close-button" onClick={onClose}>
          &times;
        </button>
        {children}
      </div>
    </div>
  );
};

export default Modal;