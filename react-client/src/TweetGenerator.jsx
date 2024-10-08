import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [topic, setTopic] = useState('');
  const [response, setResponse] = useState('');
  const [fileName, setFileName] = useState('document.txt');
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await axios.post('api/generate-tweet', {
        topic,
        file_name: fileName,
      });
      setResponse(result.data.response);
    } catch (error) {
      setResponse('Error generating tweet.');
      console.error(error);
    }
    setLoading(false);
  };

  return (
    <div className="App">
      <h1>AI Tweet Generator</h1>
      <div>
        <label>Topic:</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Enter a topic"
        />
      </div>
      <div>
        <label>File Name:</label>
        <input
          type="text"
          value={fileName}
          onChange={(e) => setFileName(e.target.value)}
          placeholder="Enter file name (e.g., document.txt)"
        />
      </div>
      <button onClick={handleGenerate} disabled={loading}>
        {loading ? 'Generating...' : 'Generate Tweet'}
      </button>
      {response && (
        <div className="response">
          <h3>Generated Tweet:</h3>
          <p>{response}</p>
        </div>
      )}
    </div>
  );
}

export default App;
