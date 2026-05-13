// src/App.js
import React, { useState } from 'react';
import axios from 'axios';
<<<<<<< Updated upstream
import './styles/App.css'; 
=======
import './styles/App.css';
>>>>>>> Stashed changes
import Sidebar from './components/Sidebar';
import ChatFeed from './components/ChatFeed';
import FloatingInput from './components/FloatingInput';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

<<<<<<< Updated upstream
=======
  // NEW: Generate a unique thread ID for this user's session
  const [threadId] = useState(() => {
    let id = sessionStorage.getItem('rosetta_thread_id');
    if (!id) {
      id = 'session_' + Math.random().toString(36).substr(2, 9);
      sessionStorage.setItem('rosetta_thread_id', id);
    }
    return id;
  });

>>>>>>> Stashed changes
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

<<<<<<< Updated upstream
    const API_URL =  process.env.REACT_APP_API_URL;

    try {
      const response = await axios.post(`${API_URL}/api/chat`, {
        query: input
=======
    // FIXED: Environment variable now takes priority
    const API_URL = process.env.BACKEND_URL || 'http://localhost:8000';

    try {
      const response = await axios.post(`${API_URL}/api/chat`, {
        query: input,
        thread_id: threadId // NEW: Send the thread ID to the backend
>>>>>>> Stashed changes
      });

      const botMsg = {
        role: 'bot',
        content: response.data.answer,
        datasource: response.data.datasource
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      console.error("API Error:", error);
      const errorMsg = {
        role: 'bot',
        content: "I encountered a severe error connecting to the RosettaRAG backend. Please ensure the server is online."
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
      <div className="flex h-screen bg-[#0B0F19] text-slate-300 font-sans selection:bg-cyan-500/30 relative overflow-hidden">
<<<<<<< Updated upstream

        {/* Background Texture Mask */}
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] pointer-events-none mix-blend-overlay z-0"></div>

        <Sidebar />

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col h-full relative z-10">

          <ChatFeed messages={messages} loading={loading} />

=======
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] pointer-events-none mix-blend-overlay z-0"></div>
        <Sidebar />
        <div className="flex-1 flex flex-col h-full relative z-10">
          <ChatFeed messages={messages} loading={loading} />
>>>>>>> Stashed changes
          <FloatingInput
              input={input}
              setInput={setInput}
              handleSend={handleSend}
              loading={loading}
          />
        </div>
      </div>
  );
}

<<<<<<< Updated upstream
export default App;
=======
export default App;
>>>>>>> Stashed changes
