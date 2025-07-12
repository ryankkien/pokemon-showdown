import React, { useState, useEffect, useRef } from 'react'
import './ShowdownBattle.css'

const ShowdownBattle = ({ battleId, currentBattle }) => {
  const iframeRef = useRef(null)
  const [showdownUrl, setShowdownUrl] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (battleId && currentBattle) {
      // Pokemon Showdown battle URLs follow the pattern: http://localhost:8000/battle-[format]-[battleid]
      // The battle format is typically something like "gen9randombattle"
      const format = currentBattle.format || 'gen9randombattle'
      const roomId = currentBattle.roomId || `battle-${format}-${battleId}`
      const battleUrl = `http://localhost:8000/${roomId}`
      setShowdownUrl(battleUrl)
      setIsLoading(true)
    }
  }, [battleId, currentBattle])

  const handleIframeLoad = () => {
    setIsLoading(false)
    
    // Try to auto-spectate the battle
    if (iframeRef.current) {
      try {
        // Send a message to the iframe to join as spectator
        const iframe = iframeRef.current
        setTimeout(() => {
          // Pokemon Showdown accepts postMessage for certain actions
          iframe.contentWindow.postMessage({
            type: 'join-battle',
            room: battleId
          }, 'http://localhost:8000')
        }, 1000)
      } catch (e) {
        console.log('Could not auto-join battle:', e)
      }
    }
  }

  if (!battleId || !currentBattle) {
    return (
      <div className="showdown-battle-container">
        <div className="no-battle">
          <h3>No Active Battle</h3>
          <p>Select a battle from the scheduler to watch it live in Pokemon Showdown</p>
        </div>
      </div>
    )
  }

  return (
    <div className="showdown-battle-container">
      <div className="showdown-header">
        <h3>Pokemon Showdown Battle View</h3>
        <div className="battle-meta">
          <span className="battle-id">Battle: {battleId}</span>
          <span className="battle-players">
            {currentBattle.player1} vs {currentBattle.player2}
          </span>
        </div>
      </div>
      
      {isLoading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Loading Pokemon Showdown battle...</p>
        </div>
      )}
      
      <div className="showdown-iframe-wrapper">
        <iframe
          ref={iframeRef}
          src={showdownUrl}
          title="Pokemon Showdown Battle"
          className="showdown-iframe"
          onLoad={handleIframeLoad}
          sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
        />
      </div>
      
      <div className="showdown-controls">
        <button 
          onClick={() => window.open(showdownUrl, '_blank')}
          className="open-external"
        >
          Open in New Tab
        </button>
        <button 
          onClick={() => iframeRef.current?.contentWindow.location.reload()}
          className="refresh-battle"
        >
          Refresh View
        </button>
      </div>
    </div>
  )
}

export default ShowdownBattle