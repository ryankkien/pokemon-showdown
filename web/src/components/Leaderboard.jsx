import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './Leaderboard.css'

const Leaderboard = ({ currentBattle, onDataUpdate }) => {
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('elo')

  useEffect(() => {
    fetchLeaderboard()
    const interval = setInterval(fetchLeaderboard, 3000) // Update every 3 seconds
    return () => clearInterval(interval)
  }, [sortBy])

  const fetchLeaderboard = async () => {
    try {
      const response = await axios.get(`/api/leaderboard?sort=${sortBy}&limit=10`)
      setLeaderboard(response.data.leaderboard)
      onDataUpdate(response.data.leaderboard)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching leaderboard:', error)
      setLoading(false)
    }
  }

  const getProviderBadge = (username) => {
    if (username.toLowerCase().includes('gpt')) return 'openai'
    if (username.toLowerCase().includes('claude')) return 'anthropic'
    if (username.toLowerCase().includes('gemini')) return 'google'
    return 'other'
  }

  const isCurrentlyBattling = (username) => {
    if (!currentBattle) return false
    return currentBattle.bot1 === username || currentBattle.bot2 === username
  }

  if (loading) {
    return (
      <div className="leaderboard loading">
        <div className="loading-spinner"></div>
        Loading rankings...
      </div>
    )
  }

  return (
    <div className="leaderboard">
      <div className="leaderboard-header">
        <h2>LLM Rankings</h2>
        <div className="sort-controls">
          <button 
            className={sortBy === 'elo' ? 'active' : ''}
            onClick={() => setSortBy('elo')}
          >
            ELO
          </button>
          <button 
            className={sortBy === 'wins' ? 'active' : ''}
            onClick={() => setSortBy('wins')}
          >
            Wins
          </button>
          <button 
            className={sortBy === 'win_rate' ? 'active' : ''}
            onClick={() => setSortBy('win_rate')}
          >
            Win %
          </button>
        </div>
      </div>

      <div className="leaderboard-content">
        {leaderboard.map((entry, index) => (
          <div 
            key={entry.username} 
            className={`leaderboard-entry rank-${entry.rank} ${isCurrentlyBattling(entry.username) ? 'battling' : ''}`}
          >
            <div className="rank">#{entry.rank}</div>
            <div className="model-info">
              <div className="model-name">
                {entry.username}
                <span className={`provider-badge ${getProviderBadge(entry.username)}`}>
                  {getProviderBadge(entry.username)}
                </span>
                {isCurrentlyBattling(entry.username) && (
                  <span className="battle-indicator">⚔️ LIVE</span>
                )}
              </div>
              <div className="model-stats">
                <span className="elo">{entry.elo_rating} ELO</span>
                <span className="record">{entry.wins}-{entry.losses}-{entry.draws}</span>
                <span className="win-rate">{entry.win_rate}%</span>
              </div>
            </div>
            <div className="recent-form">
              {entry.recent_form.split('').map((result, idx) => (
                <span key={idx} className={`form-${result.toLowerCase()}`}>
                  {result}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Leaderboard