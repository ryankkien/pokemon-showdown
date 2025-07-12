import React, { useState, useEffect } from 'react'
import LiveBattle from './components/LiveBattle'
import Leaderboard from './components/Leaderboard'
import ChatIntegration from './components/ChatIntegration'
import BattleScheduler from './components/BattleScheduler'
import './App.css'

function App() {
  const [currentBattle, setCurrentBattle] = useState(null)
  const [leaderboardData, setLeaderboardData] = useState([])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Pokemon Showdown LLM Battle Arena</h1>
        <p>Watch AI models compete in real-time Pokemon battles</p>
      </header>

      <main className="app-main">
        <div className="battle-container">
          <div className="battle-and-chat">
            <div className="battle-view">
              <LiveBattle currentBattle={currentBattle} />
            </div>
            <div className="chat-panel">
              <ChatIntegration />
            </div>
          </div>
          
          <div className="battle-info">
            <BattleScheduler onBattleUpdate={setCurrentBattle} />
          </div>
        </div>

        <div className="leaderboard-container">
          <Leaderboard 
            data={leaderboardData} 
            currentBattle={currentBattle}
            onDataUpdate={setLeaderboardData}
          />
        </div>
      </main>
    </div>
  )
}

export default App