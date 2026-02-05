import { useState, useEffect, useRef } from 'react'
import './App.css'
import logo from './assets/logo.png'

function App() {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [events, setEvents] = useState([{ type: 'info', text: 'Studio Agent Connected. Awaiting objective.' }])
  const [sessionHistory, setSessionHistory] = useState([])
  const [context, setContext] = useState({ objects: [] })
  const [selectedImage, setSelectedImage] = useState(null) // Base64 image state
  
  const scrollRef = useRef(null)
  
  // Extract latest state for the dashboard
  const latestUser = events.slice().reverse().find(e => e.type === 'user');
  const latestThought = events.slice().reverse().find(e => e.type === 'thought');
  const latestTool = events.slice().reverse().find(e => e.type === 'tool');
  const latestResult = events.slice().reverse().find(e => e.type === 'result');

  // Auto-scroll chat
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => setSelectedImage(reader.result);
      reader.readAsDataURL(file);
    }
  }

  const handleInteract = async () => {
    if ((!input && !selectedImage) || loading) return;
    const userMsg = input;
    const imgData = selectedImage;
    
    setInput('');
    setSelectedImage(null);
    setLoading(true);
    
    // Add user message with image preview to UI
    setEvents(prev => [...prev, { 
      type: 'user', 
      text: userMsg, 
      image: imgData 
    }]);

    try {
      const response = await fetch('http://localhost:8000/interact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMsg || "Analyze this image and create a 3D scene based on it.", 
          session_history: sessionHistory,
          image: imgData // Send base64 image
        }),
      });
      
      const data = await response.json();
      
      setEvents(prev => [
        ...prev, 
        { type: 'thought', text: data.thought },
        { type: 'tool', text: `Tool Call: BlenderExecutor`, code: data.code },
        { type: 'result', text: data.execution.success ? 'Execution Successful' : 'Execution Failed', success: data.execution.success, output: data.execution.output, error: data.execution.error }
      ]);

      if (data.execution.success) {
        setSessionHistory(prev => [...prev, data.code]);
      }
      setContext(data.new_context);
    } catch (err) {
      setEvents(prev => [...prev, { type: 'error', text: 'System Error: Tool communication failed.' }]);
    } finally {
      setLoading(false);
    }
  }

  const handleReset = async () => {
    await fetch('http://localhost:8000/reset', { method: 'POST' });
    setEvents([{ type: 'info', text: 'Scene reset. Session history cleared.' }]);
    setSessionHistory([]);
    setContext({ objects: [] });
  }

  return (
    <div className="clixor-studio">
      <header className="studio-header">
        <div className="logo-container">
          <img src={logo} alt="Clixor Logo" className="logo-img" />
          <div className="logo-badge">AI 3D ANIMATION STUDIO</div>
        </div>
        <div className="status-indicator">
          {loading ? 'PROCESSING...' : 'READY'} <span className={`status-dot ${loading ? 'busy' : 'ready'}`}></span>
        </div>
      </header>

      <div className="main-layout">
        
        {/* LEFT SIDE: CHAT STREAM */}
        <div className="left-panel chat-container">
          <div className="panel-header">CREATIVE SESSION</div>
          <div className="event-stream">
            {events.map((ev, i) => (
              <div key={i} className={`chat-bubble ${ev.type}`}>
                <div className="bubble-label">{ev.type.toUpperCase()}</div>
                <div className="bubble-content">
                  {ev.image && <img src={ev.image} alt="User Upload" className="chat-img-preview" />}
                  {ev.text}
                  {ev.code && <div className="code-preview">Python Code Generated (See Dashboard)</div>}
                  {ev.output && <pre className="output-preview">{ev.output}</pre>}
                  {ev.error && <pre className="error-preview">{ev.error}</pre>}
                </div>
              </div>
            ))}
            <div ref={scrollRef} />
          </div>
          
          <div className="input-area">
             {/* Image Preview Area */}
            {selectedImage && (
              <div className="input-img-preview">
                <img src={selectedImage} alt="Selected" />
                <button className="remove-img" onClick={() => setSelectedImage(null)}>×</button>
              </div>
            )}
            
            <label className="icon-btn-upload">
              <input type="file" accept="image/*" onChange={handleImageSelect} hidden />
              📷
            </label>
            
            <input 
              value={input} 
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleInteract()}
              placeholder={selectedImage ? "Describe what to do with this image..." : "What should we create today?"}
            />
            <button className="send-btn" onClick={handleInteract} disabled={loading}>
              ➤
            </button>
          </div>
        </div>

        {/* RIGHT SIDE: DASHBOARD GRID */}
        <div className="right-panel dashboard-grid">
          
          {/* TOP LEFT: PLANNER */}
          <div className="dash-card plan-card">
            <div className="card-header">PLANNER</div>
            <div className="card-content">
              {latestThought ? (
                <div className="thought-display">"{latestThought.text}"</div>
              ) : (
                <div className="empty-state">Waiting for agent reasoning...</div>
              )}
            </div>
          </div>

          {/* TOP RIGHT: VIEWPORT CONTEXT */}
          <div className="dash-card viewport-card">
            <div className="card-header">
              <span>SCENE CONTEXT</span>
              <button className="sm-btn" onClick={handleReset}>RESET VIEWPORT</button>
            </div>
            <div className="card-content scroll-y">
              {context.objects.length > 0 ? (
                <div className="obj-grid">
                  {context.objects.map((obj, i) => (
                    <div key={i} className="obj-tag">
                      <span className="icon">{obj.type === 'MESH' ? 'cube' : 'stop'}</span>
                      <span className="name">{obj.name}</span>
                      <span className="loc">{`[${obj.location.map(n=>Math.round(n)).join(',')}]`}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">Scene is empty</div>
              )}
            </div>
          </div>

          {/* BOTTOM LEFT: SUMMARY */}
          <div className="dash-card summary-card">
            <div className="card-header">SESSION SUMMARY</div>
            <div className="card-content summary-content">
               <div className="summary-item">
                 <div className="s-label">ACTIVE GOAL</div>
                 <div className="s-value">{latestUser ? latestUser.text : "Idle"}</div>
               </div>
               <div className="summary-item">
                 <div className="s-label">LAST ACTION</div>
                 <div className="s-value status">
                   {latestResult ? (latestResult.success ? "✅ Success" : "❌ Failed") : "Waiting..."}
                 </div>
               </div>
               <div className="summary-item">
                 <div className="s-label">OBJECTS IN SCENE</div>
                 <div className="s-value highlight">{context.objects.length}</div>
               </div>
            </div>
          </div>

          {/* BOTTOM RIGHT: CODE (MINIMIZED) */}
          <div className="dash-card code-card">
            <div className="card-header">GENERATED SCRIPT</div>
            <div className="card-content code-view">
              {latestTool ? (
                <pre>{latestTool.code}</pre>
              ) : (
                <div className="empty-state">// Code generation pending...</div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

export default App