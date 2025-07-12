import React, { useState, useEffect } from 'react'
import LiveBattle from './components/LiveBattle'
import ShowdownBattle from './components/ShowdownBattle'
import Leaderboard from './components/Leaderboard'
import BattleScheduler from './components/BattleScheduler'
import './App.css'

function App() {
  const [currentBattle, setCurrentBattle] = useState(null)
  const [leaderboardData, setLeaderboardData] = useState([])
  const [viewMode, setViewMode] = useState('split') // 'split', 'custom', 'showdown'
  const [battleId, setBattleId] = useState(null)

  // Extract battle ID when a new battle starts
  useEffect(() => {
    if (currentBattle && currentBattle.id) {
      setBattleId(currentBattle.id)
    }
  }, [currentBattle])

  return (
    <div className="app">
      <header className="app-header">
        <h1>Pokemon Showdown LLM Battle Arena</h1>
        <p>Watch AI models compete in real-time Pokemon battles</p>
        <div className="view-mode-toggle">
          <button 
            className={viewMode === 'split' ? 'active' : ''}
            onClick={() => setViewMode('split')}
          >
            Split View
          </button>
          <button 
            className={viewMode === 'custom' ? 'active' : ''}
            onClick={() => setViewMode('custom')}
          >
            Custom View
          </button>
          <button 
            className={viewMode === 'showdown' ? 'active' : ''}
            onClick={() => setViewMode('showdown')}
          >
            Showdown View
          </button>
        </div>
      </header>

      <main className="app-main">
        <div className="main-content">
          <div className="left-panel">
            <div className="battle-scheduler-section">
              <BattleScheduler onBattleUpdate={setCurrentBattle} />
            </div>
            <div className="leaderboard-section">
              <Leaderboard 
                data={leaderboardData} 
                currentBattle={currentBattle}
                onDataUpdate={setLeaderboardData}
              />
            </div>
          </div>

          <div className="center-panel">
            {viewMode === 'split' && (
              <div className="split-view">
                <div className="custom-battle-view">
                  <LiveBattle currentBattle={currentBattle} />
                </div>
                <div className="showdown-battle-view">
                  <ShowdownBattle battleId={battleId} currentBattle={currentBattle} />
                </div>
              </div>
            )}
            {viewMode === 'custom' && (
              <div className="full-custom-view">
                <LiveBattle currentBattle={currentBattle} />
              </div>
            )}
            {viewMode === 'showdown' && (
              <div className="full-showdown-view">
                <ShowdownBattle battleId={battleId} currentBattle={currentBattle} />
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  )
}

export default App