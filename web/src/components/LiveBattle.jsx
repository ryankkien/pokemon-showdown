import React, { useState, useEffect } from 'react'
import io from 'socket.io-client'
import './LiveBattle.css'

const LiveBattle = ({ currentBattle }) => {
  const [battleState, setBattleState] = useState(null)
  const [battleLog, setBattleLog] = useState([])
  const [socket, setSocket] = useState(null)
  const [isDelayedMove, setIsDelayedMove] = useState(false)

  useEffect(() => {
    // Connect to battle relay server
    const newSocket = io('http://localhost:5001', {
      transports: ['websocket'],
    })

    newSocket.on('connect', () => {
      console.log('Connected to battle relay')
    })

    newSocket.on('battleUpdate', (data) => {
      setBattleState(data.state)
      if (data.log) {
        setBattleLog(prev => [...prev, data.log].slice(-50)) // Keep last 50 logs
      }
      setIsDelayedMove(data.isDelayed || false)
    })

    newSocket.on('battleEnd', (data) => {
      console.log('Battle ended:', data)
    })

    setSocket(newSocket)

    return () => {
      newSocket.disconnect()
    }
  }, [])

  useEffect(() => {
    if (socket && currentBattle) {
      socket.emit('subscribeToBattle', { battleId: currentBattle.id })
    }
  }, [socket, currentBattle])

  if (!currentBattle || !battleState) {
    return (
      <div className="live-battle no-battle">
        <div className="no-battle-content">
          <h2>No Active Battle</h2>
          <p>Waiting for the next battle to start...</p>
          <div className="waiting-indicator">
            <div className="pulse"></div>
          </div>
        </div>
      </div>
    )
  }

  const { p1, p2, turn } = battleState

  return (
    <div className="live-battle">
      <div className="battle-header">
        <h2>Live Battle</h2>
        <div className="battle-info">
          <span className="turn">Turn {turn || 0}</span>
          <span className="format">{currentBattle.format}</span>
          {isDelayedMove && <span className="delay-indicator">Move Delayed...</span>}
        </div>
      </div>

      <div className="battle-field">
        <div className="trainer p1">
          <div className="trainer-info">
            <h3>{p1?.name || 'Player 1'}</h3>
            <div className="team-preview">
              {p1?.team?.map((pokemon, idx) => (
                <div 
                  key={idx} 
                  className={`pokemon-icon ${pokemon.fainted ? 'fainted' : ''} ${pokemon.active ? 'active' : ''}`}
                  title={pokemon.name}
                >
                  <img 
                    src={`https://play.pokemonshowdown.com/sprites/ani/${pokemon.speciesId}.gif`}
                    alt={pokemon.name}
                    onError={(e) => {
                      e.target.src = `https://play.pokemonshowdown.com/sprites/ani-shiny/${pokemon.speciesId}.gif`
                    }}
                  />
                  <div className="hp-bar">
                    <div 
                      className="hp-fill" 
                      style={{ width: `${pokemon.hp}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          {p1?.active && (
            <div className="active-pokemon">
              <img 
                src={`https://play.pokemonshowdown.com/sprites/ani-back/${p1.active.speciesId}.gif`}
                alt={p1.active.name}
                onError={(e) => {
                  e.target.src = `https://play.pokemonshowdown.com/sprites/ani-back-shiny/${p1.active.speciesId}.gif`
                }}
              />
              <div className="pokemon-status">
                <div className="name">{p1.active.name}</div>
                <div className="hp">{p1.active.hp}% HP</div>
                {p1.active.status && <div className="status">{p1.active.status}</div>}
              </div>
            </div>
          )}
        </div>

        <div className="trainer p2">
          <div className="trainer-info">
            <h3>{p2?.name || 'Player 2'}</h3>
            <div className="team-preview">
              {p2?.team?.map((pokemon, idx) => (
                <div 
                  key={idx} 
                  className={`pokemon-icon ${pokemon.fainted ? 'fainted' : ''} ${pokemon.active ? 'active' : ''}`}
                  title={pokemon.name}
                >
                  <img 
                    src={`https://play.pokemonshowdown.com/sprites/ani/${pokemon.speciesId}.gif`}
                    alt={pokemon.name}
                    onError={(e) => {
                      e.target.src = `https://play.pokemonshowdown.com/sprites/ani-shiny/${pokemon.speciesId}.gif`
                    }}
                  />
                  <div className="hp-bar">
                    <div 
                      className="hp-fill" 
                      style={{ width: `${pokemon.hp}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
          {p2?.active && (
            <div className="active-pokemon">
              <img 
                src={`https://play.pokemonshowdown.com/sprites/ani/${p2.active.speciesId}.gif`}
                alt={p2.active.name}
                onError={(e) => {
                  e.target.src = `https://play.pokemonshowdown.com/sprites/ani-shiny/${p2.active.speciesId}.gif`
                }}
              />
              <div className="pokemon-status">
                <div className="name">{p2.active.name}</div>
                <div className="hp">{p2.active.hp}% HP</div>
                {p2.active.status && <div className="status">{p2.active.status}</div>}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="battle-log">
        <h3>Battle Log</h3>
        <div className="log-content">
          {battleLog.map((log, idx) => (
            <div key={idx} className="log-entry">
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default LiveBattle