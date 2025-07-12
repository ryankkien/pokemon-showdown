import React, { useState, useEffect } from 'react'
import './ChatIntegration.css'

const ChatIntegration = () => {
  // Local Pokemon Showdown instance - should be running on the same server
  // The default showdown runs on port 8000
  const [chatUrl, setChatUrl] = useState('http://localhost:8000')
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Check if local showdown is running
    checkShowdownConnection()
  }, [])

  const checkShowdownConnection = async () => {
    try {
      // Try to connect to local showdown
      const response = await fetch(chatUrl, { mode: 'no-cors' })
      setIsConnected(true)
      setError(null)
    } catch (err) {
      setIsConnected(false)
      setError('Local Pokemon Showdown not detected. Make sure the server is running on port 8000.')
    }
  }

  if (error) {
    return (
      <div className="chat-integration">
        <div className="chat-header">
          <h3>Battle Chat</h3>
        </div>
        <div className="chat-container chat-error">
          <div className="error-message">
            <p>{error}</p>
            <p className="error-hint">
              Start the local server with: <code>cd server/pokemon-showdown && node pokemon-showdown</code>
            </p>
            <button onClick={checkShowdownConnection}>Retry Connection</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-integration">
      <div className="chat-header">
        <h3>Battle Chat</h3>
        <span className="connection-status">
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </span>
      </div>
      <div className="chat-container">
        <iframe
          src={chatUrl}
          title="Pokemon Showdown Chat"
          className="chat-iframe"
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          onLoad={() => setIsConnected(true)}
          onError={() => setIsConnected(false)}
        />
      </div>
    </div>
  )
}

export default ChatIntegration