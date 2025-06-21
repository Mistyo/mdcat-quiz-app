import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [file, setFile] = useState(null);
  const [mcqs, setMcqs] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a PDF file first.');
      return;
    }

    setLoading(true);
    setError('');
    setMcqs([]);
    setAnswers({});

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        'https://organic-space-memory-459g4rjrgvr2q576-5000.app.github.dev/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      if (response.data.mcqs && response.data.mcqs.length > 0) {
        setMcqs(response.data.mcqs);
      } else {
        setError('No MCQs found in the PDF.');
      }
    } catch (err) {
      console.error(err);
      setError('Something went wrong while uploading the PDF.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (index, option) => {
    setAnswers({ ...answers, [index]: option });
  };

  const downloadAnswers = () => {
    let content = '';
    for (let i = 0; i < mcqs.length; i++) {
      const selected = answers[i] || 'Not answered';
      content += `${i + 1}. ${selected}\n`;
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'my_answers.txt';
    a.click();

    window.URL.revokeObjectURL(url);
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial' }}>
      <h2>MDCAT PDF Quiz Generator</h2>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={handleUpload} style={{ marginLeft: '10px' }}>
        Upload PDF
      </button>

      {loading && <p>⏳ Processing PDF... please wait.</p>}
      {error && <p style={{ color: 'red' }}>⚠️ {error}</p>}

      {mcqs.length > 0 && (
        <div style={{ marginTop: '30px' }}>
          <h3>Interactive Quiz</h3>
          {mcqs.map((mcq, index) => {
            const optionLabels = ['A', 'B', 'C', 'D'];
            return (
              <div
                key={index}
                style={{
                  marginBottom: '20px',
                  borderBottom: '1px solid #ccc',
                  paddingBottom: '10px',
                }}
              >
                <p>
                  <strong>Q{index + 1}:</strong> {mcq.question}
                </p>
                {mcq.options.map((opt, i) => (
                  <div key={i}>
                    <label>
                      <input
                        type="radio"
                        name={`q${index}`}
                        value={optionLabels[i]}
                        checked={answers[index] === optionLabels[i]}
                        onChange={() => handleSelect(index, optionLabels[i])}
                      />{' '}
                      {optionLabels[i]}. {opt}
                    </label>
                  </div>
                ))}
              </div>
            );
          })}

          <button
            onClick={downloadAnswers}
            style={{
              padding: '10px 15px',
              fontSize: '16px',
              marginTop: '20px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
            }}
          >
            Submit & Download Answer Sheet
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
