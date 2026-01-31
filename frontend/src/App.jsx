import { useState } from 'react'
import './App.css'

function App() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleGenerate = async () => {
    if (!prompt) return;
    
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Note: In a real app, you'd configure a proxy in vite.config.js
      // or use a full URL if CORS is allowed. 
      // For this prototype, ensure backend allows CORS or use proxy.
      // We will assume a proxy is set up or direct call works for now (we might need to add cors to backend).
      const response = await fetch('http://localhost:8000/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <header>
        <h1>Gemini Animation Studio</h1>
        <p>Powered by Gemini 3 (Mock) & Blender</p>
      </header>

      <div className="input-section">
        <input 
          type="text" 
          placeholder="Describe your 3D scene (e.g., 'A cyberpunk city with neon lights')..." 
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
        />
        <button onClick={handleGenerate} disabled={loading}>
          {loading ? 'Generating...' : 'Create'}
        </button>
      </div>

      {error && <div className="card" style={{borderColor: 'var(--error)'}}>
        <h2 style={{color: 'var(--error)'}}>Error</h2>
        <p>{error}</p>
      </div>}

      {result && (
        <div className="dashboard">
          <div className="card">
            <h2>🎬 Director Agent</h2>
            <div className="agent-output">
              {result.plan}
            </div>
          </div>

          <div className="card">
            <h2>🎨 Tech Artist Agent</h2>
            <div className="agent-output">
              <div className="code-block">
                {result.code}
              </div>
            </div>
          </div>

          <div className="card">
            <h2>⚙️ Blender Execution</h2>
            <div className="agent-output">
               <div>
                  Status: 
                  <span className={result.execution_result.success ? "status-badge status-success" : "status-badge status-error"}>
                    {result.execution_result.success ? "SUCCESS" : "FAILED"}
                  </span>
               </div>
               <pre>{result.execution_result.output}</pre>
               {result.execution_result.error && <pre style={{color: 'var(--error)'}}>{result.execution_result.error}</pre>}
            </div>
          </div>

          <div className="card">
            <h2>👁️ Vision QA Agent</h2>
            <div className="agent-output">
              {result.qa_feedback}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App