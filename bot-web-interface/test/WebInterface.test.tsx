import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../src/App';
import LeaderboardServer from '../src/services/LeaderboardServer';
import BattleRelayServer from '../src/services/BattleRelayServer';

// Mock the server modules
vi.mock('../src/services/LeaderboardServer');
vi.mock('../src/services/BattleRelayServer');

describe('Web Interface Startup and Initialization', () => {
  let mockLeaderboardServer: any;
  let mockBattleRelayServer: any;

  beforeEach(() => {
    // Setup mocks
    mockLeaderboardServer = {
      start: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn().mockResolvedValue(undefined),
      getLeaderboard: vi.fn().mockResolvedValue([]),
      updateBattleResult: vi.fn()
    };

    mockBattleRelayServer = {
      start: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn().mockResolvedValue(undefined),
      broadcastBattleUpdate: vi.fn()
    };

    // Mock the constructors
    (LeaderboardServer as any).mockImplementation(() => mockLeaderboardServer);
    (BattleRelayServer as any).mockImplementation(() => mockBattleRelayServer);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render the main App component', () => {
    render(<App />);
    expect(screen.getByText(/Pokemon Showdown Battle View/i)).toBeInTheDocument();
  });

  it('should display view mode buttons', () => {
    render(<App />);
    expect(screen.getByText('Live Battle')).toBeInTheDocument();
    expect(screen.getByText('Showdown Battle')).toBeInTheDocument();
    expect(screen.getByText('Leaderboard')).toBeInTheDocument();
  });

  it('should switch between view modes', async () => {
    render(<App />);
    
    // Click Live Battle
    fireEvent.click(screen.getByText('Live Battle'));
    await waitFor(() => {
      expect(screen.getByText(/Battle not started yet/i)).toBeInTheDocument();
    });

    // Click Showdown Battle
    fireEvent.click(screen.getByText('Showdown Battle'));
    await waitFor(() => {
      expect(screen.getByTitle('Pokemon Showdown Battle')).toBeInTheDocument();
    });

    // Click Leaderboard
    fireEvent.click(screen.getByText('Leaderboard'));
    await waitFor(() => {
      expect(screen.getByText(/Bot Leaderboard/i)).toBeInTheDocument();
    });
  });

  it('should start backend servers on initialization', async () => {
    const { container } = render(<App />);
    
    // Wait for initialization
    await waitFor(() => {
      expect(LeaderboardServer).toHaveBeenCalled();
      expect(BattleRelayServer).toHaveBeenCalled();
    });

    expect(mockLeaderboardServer.start).toHaveBeenCalled();
    expect(mockBattleRelayServer.start).toHaveBeenCalled();
  });

  it('should handle server startup errors gracefully', async () => {
    mockLeaderboardServer.start.mockRejectedValue(new Error('Server start failed'));
    
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    render(<App />);
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to start servers'),
        expect.any(Error)
      );
    });

    consoleSpy.mockRestore();
  });
});