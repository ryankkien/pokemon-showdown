import React, { useState, useEffect } from 'react'
import LiveBattle from './components/LiveBattle'
import Leaderboard from './components/Leaderboard'
import ChatIntegration from './components/ChatIntegration'
import BattleScheduler from './components/BattleScheduler'
import './App.css'

function App() {
  const [currentBattle, setCurrentBattle] = useState(null)
  const [leaderboardData, setLeaderboardData] = useState([])
  const [showChat, setShowChat] = useState(true)

  return (
    <div className="app">
      <header className="app-header">
        <h1>Pokemon Showdown LLM Battle Arena</h1>
        <p>Watch AI models compete in real-time Pokemon battles</p>
      </header>

      <main className="app-main">
        <div className="battle-section">
          <LiveBattle currentBattle={currentBattle} />
          <BattleScheduler onBattleUpdate={setCurrentBattle} />
        </div>

        <div className="sidebar">
          <div className="leaderboard-section">
            <Leaderboard 
              data={leaderboardData} 
              currentBattle={currentBattle}
              onDataUpdate={setLeaderboardData}
            />
          </div>

          {showChat && (
            <div className="chat-section">
              <ChatIntegration />
            </div>
          )}
        </div>
      </main>

      <div className="chat-toggle">
        <button onClick={() => setShowChat(!showChat)}>
          {showChat ? 'Hide Chat' : 'Show Chat'}
        </button>
      </div>
    </div>
  )
}

export default App