import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './BattleScheduler.css'

const BattleScheduler = ({ onBattleUpdate }) => {
  const [nextBattleTime, setNextBattleTime] = useState(null)
  const [currentStatus, setCurrentStatus] = useState('idle')
  const [selectedFormat, setSelectedFormat] = useState('gen9randombattle')
  const [countdown, setCountdown] = useState(null)

  const formats = [
    { value: 'gen9randombattle', label: 'Gen 9 Random Battle' },
    { value: 'gen8randombattle', label: 'Gen 8 Random Battle' },
    { value: 'gen7randombattle', label: 'Gen 7 Random Battle' },
    { value: 'gen6randombattle', label: 'Gen 6 Random Battle' },
  ]

  useEffect(() => {
    checkBattleStatus()
    const interval = setInterval(checkBattleStatus, 5000) // Check every 5 seconds
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (nextBattleTime) {
      const interval = setInterval(() => {
        const now = Date.now()
        const timeLeft = nextBattleTime - now
        if (timeLeft > 0) {
          const minutes = Math.floor(timeLeft / 60000)
          const seconds = Math.floor((timeLeft % 60000) / 1000)
          setCountdown(`${minutes}:${seconds.toString().padStart(2, '0')}`)
        } else {
          setCountdown(null)
        }
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [nextBattleTime])

  const checkBattleStatus = async () => {
    try {
      const response = await axios.get('/api/battle-status')
      setCurrentStatus(response.data.status)
      
      if (response.data.currentBattle) {
        onBattleUpdate(response.data.currentBattle)
      } else {
        onBattleUpdate(null)
      }
      
      if (response.data.nextBattleTime) {
        setNextBattleTime(new Date(response.data.nextBattleTime).getTime())
      }
    } catch (error) {
      console.error('Error checking battle status:', error)
    }
  }

  const startBattle = async () => {
    try {
      const response = await axios.post('/api/start-battle', {
        format: selectedFormat
      })
      
      if (response.data.success) {
        setCurrentStatus('battling')
        onBattleUpdate(response.data.battle)
      }
    } catch (error) {
      console.error('Error starting battle:', error)
    }
  }

  const scheduleNextBattle = async () => {
    try {
      const response = await axios.post('/api/schedule-battle', {
        format: selectedFormat,
        delayMinutes: 5
      })
      
      if (response.data.success) {
        setNextBattleTime(new Date(response.data.scheduledTime).getTime())
      }
    } catch (error) {
      console.error('Error scheduling battle:', error)
    }
  }

  return (
    <div className="battle-scheduler">
      <div className="scheduler-header">
        <h3>Battle Control</h3>
        <div className="status-indicator">
          <span className={`status-dot ${currentStatus}`}></span>
          <span className="status-text">
            {currentStatus === 'battling' ? 'Battle in Progress' : 
             currentStatus === 'scheduled' ? 'Battle Scheduled' : 'Idle'}
          </span>
        </div>
      </div>

      <div className="scheduler-content">
        <div className="format-selector">
          <label>Battle Format:</label>
          <select 
            value={selectedFormat} 
            onChange={(e) => setSelectedFormat(e.target.value)}
            disabled={currentStatus === 'battling'}
          >
            {formats.map(format => (
              <option key={format.value} value={format.value}>
                {format.label}
              </option>
            ))}
          </select>
        </div>

        {currentStatus === 'idle' && (
          <div className="actions">
            <button 
              className="btn-primary"
              onClick={startBattle}
            >
              Start Battle Now
            </button>
            <button 
              className="btn-secondary"
              onClick={scheduleNextBattle}
            >
              Schedule in 5 Minutes
            </button>
          </div>
        )}

        {currentStatus === 'scheduled' && countdown && (
          <div className="countdown">
            <p>Next battle starts in:</p>
            <div className="countdown-timer">{countdown}</div>
          </div>
        )}

        {currentStatus === 'battling' && (
          <div className="battle-info">
            <p>Battle in progress...</p>
            <div className="progress-bar">
              <div className="progress-fill"></div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BattleScheduler