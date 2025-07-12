import React from 'react'
import './ChatIntegration.css'

const ChatIntegration = () => {
  // Pokemon Showdown chat URL - this will embed the actual showdown chat
  const chatUrl = 'https://play.pokemonshowdown.com/'

  return (
    <div className="chat-integration">
      <div className="chat-header">
        <h3>Pokemon Showdown Chat</h3>
        <a 
          href={chatUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="open-external"
        >
          Open in new tab ↗
        </a>
      </div>
      <div className="chat-container">
        <iframe
          src={chatUrl}
          title="Pokemon Showdown Chat"
          className="chat-iframe"
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
        />
      </div>
    </div>
  )
}

export default ChatIntegration