import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import Leaderboard from '../src/components/Leaderboard';
import LeaderboardServer from '../src/services/LeaderboardServer';

// Mock fetch
global.fetch = vi.fn();

// Mock LeaderboardServer
vi.mock('../src/services/LeaderboardServer');

describe('Leaderboard Functionality', () => {
  let mockLeaderboardServer: any;

  beforeEach(() => {
    mockLeaderboardServer = {
      getLeaderboard: vi.fn().mockResolvedValue([
        { name: 'BotAlpha', wins: 10, losses: 2, winRate: 83.33, elo: 1650 },
        { name: 'BotBeta', wins: 8, losses: 4, winRate: 66.67, elo: 1550 },
        { name: 'BotGamma', wins: 5, losses: 7, winRate: 41.67, elo: 1450 },
        { name: 'BotDelta', wins: 3, losses: 9, winRate: 25.00, elo: 1350 }
      ]),
      updateBattleResult: vi.fn(),
      getBattleHistory: vi.fn().mockResolvedValue([
        {
          id: 'battle-1',
          winner: 'BotAlpha',
          loser: 'BotBeta',
          timestamp: Date.now() - 3600000,
          duration: 180,
          turns: 25
        },
        {
          id: 'battle-2',
          winner: 'BotGamma',
          loser: 'BotDelta',
          timestamp: Date.now() - 7200000,
          duration: 240,
          turns: 30
        }
      ])
    };

    (LeaderboardServer as any).mockImplementation(() => mockLeaderboardServer);

    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockLeaderboardServer.getLeaderboard()
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Leaderboard Display', () => {
    it('should render the leaderboard component', async () => {
      render(<Leaderboard />);
      
      expect(screen.getByText(/Bot Leaderboard/i)).toBeInTheDocument();
      
      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
      });
    });

    it('should display bot rankings', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
        expect(screen.getByText('BotBeta')).toBeInTheDocument();
        expect(screen.getByText('BotGamma')).toBeInTheDocument();
        expect(screen.getByText('BotDelta')).toBeInTheDocument();
      });
    });

    it('should show win/loss records', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('10-2')).toBeInTheDocument(); // BotAlpha
        expect(screen.getByText('8-4')).toBeInTheDocument();  // BotBeta
        expect(screen.getByText('5-7')).toBeInTheDocument();  // BotGamma
        expect(screen.getByText('3-9')).toBeInTheDocument();  // BotDelta
      });
    });

    it('should display win rates', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('83.33%')).toBeInTheDocument();
        expect(screen.getByText('66.67%')).toBeInTheDocument();
        expect(screen.getByText('41.67%')).toBeInTheDocument();
        expect(screen.getByText('25.00%')).toBeInTheDocument();
      });
    });

    it('should show ELO ratings', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('1650')).toBeInTheDocument();
        expect(screen.getByText('1550')).toBeInTheDocument();
        expect(screen.getByText('1450')).toBeInTheDocument();
        expect(screen.getByText('1350')).toBeInTheDocument();
      });
    });
  });

  describe('Sorting and Filtering', () => {
    it('should sort by different columns', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
      });

      // Click on Wins header to sort by wins
      const winsHeader = screen.getByText('Wins');
      fireEvent.click(winsHeader);

      // First bot should still be BotAlpha (10 wins)
      const rows = screen.getAllByRole('row');
      expect(rows[1]).toHaveTextContent('BotAlpha');

      // Click again to reverse sort
      fireEvent.click(winsHeader);
      expect(rows[1]).toHaveTextContent('BotDelta');
    });

    it('should filter bots by name', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search bots/i);
      fireEvent.change(searchInput, { target: { value: 'Alpha' } });

      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
        expect(screen.queryByText('BotBeta')).not.toBeInTheDocument();
        expect(screen.queryByText('BotGamma')).not.toBeInTheDocument();
      });
    });

    it('should filter by minimum games played', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
      });

      const minGamesInput = screen.getByLabelText(/Minimum games/i);
      fireEvent.change(minGamesInput, { target: { value: '12' } });

      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument(); // 12 games
        expect(screen.getByText('BotBeta')).toBeInTheDocument();  // 12 games
        expect(screen.queryByText('BotGamma')).not.toBeInTheDocument(); // 12 games
        expect(screen.queryByText('BotDelta')).not.toBeInTheDocument(); // 12 games
      });
    });
  });

  describe('Real-time Updates', () => {
    it('should auto-refresh leaderboard', async () => {
      vi.useFakeTimers();
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
      });

      // Update mock data
      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => [
          { name: 'BotAlpha', wins: 11, losses: 2, winRate: 84.62, elo: 1670 },
          { name: 'BotBeta', wins: 8, losses: 5, winRate: 61.54, elo: 1540 }
        ]
      });

      // Fast-forward 30 seconds (auto-refresh interval)
      vi.advanceTimersByTime(30000);

      await waitFor(() => {
        expect(screen.getByText('11-2')).toBeInTheDocument();
        expect(screen.getByText('84.62%')).toBeInTheDocument();
      });

      vi.useRealTimers();
    });

    it('should handle WebSocket updates for live battles', async () => {
      const mockWS = {
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        send: vi.fn(),
        close: vi.fn()
      };

      global.WebSocket = vi.fn(() => mockWS) as any;

      render(<Leaderboard />);

      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
      });

      // Simulate WebSocket message
      const messageHandler = mockWS.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )[1];

      messageHandler({
        data: JSON.stringify({
          type: 'battle-complete',
          winner: 'BotAlpha',
          loser: 'BotBeta',
          updates: [
            { name: 'BotAlpha', wins: 11, losses: 2, winRate: 84.62, elo: 1670 },
            { name: 'BotBeta', wins: 8, losses: 5, winRate: 61.54, elo: 1540 }
          ]
        })
      });

      await waitFor(() => {
        expect(screen.getByText('11-2')).toBeInTheDocument();
      });
    });
  });

  describe('Battle History', () => {
    it('should display recent battles', async () => {
      render(<Leaderboard />);
      
      const historyButton = screen.getByText(/Battle History/i);
      fireEvent.click(historyButton);

      await waitFor(() => {
        expect(screen.getByText(/BotAlpha vs BotBeta/i)).toBeInTheDocument();
        expect(screen.getByText(/BotGamma vs BotDelta/i)).toBeInTheDocument();
      });
    });

    it('should show battle details', async () => {
      render(<Leaderboard />);
      
      const historyButton = screen.getByText(/Battle History/i);
      fireEvent.click(historyButton);

      await waitFor(() => {
        expect(screen.getByText(/25 turns/i)).toBeInTheDocument();
        expect(screen.getByText(/30 turns/i)).toBeInTheDocument();
        expect(screen.getByText(/3 minutes/i)).toBeInTheDocument();
        expect(screen.getByText(/4 minutes/i)).toBeInTheDocument();
      });
    });
  });

  describe('Statistics and Analytics', () => {
    it('should display overall statistics', async () => {
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/Total Battles: 24/i)).toBeInTheDocument(); // Sum of all games
        expect(screen.getByText(/Active Bots: 4/i)).toBeInTheDocument();
      });
    });

    it('should show performance trends', async () => {
      render(<Leaderboard />);
      
      const trendsButton = screen.getByText(/Performance Trends/i);
      fireEvent.click(trendsButton);

      await waitFor(() => {
        expect(screen.getByTestId('performance-chart')).toBeInTheDocument();
      });
    });

    it('should calculate and display matchup statistics', async () => {
      mockLeaderboardServer.getMatchupStats = vi.fn().mockResolvedValue({
        'BotAlpha': {
          'BotBeta': { wins: 3, losses: 1 },
          'BotGamma': { wins: 2, losses: 0 },
          'BotDelta': { wins: 5, losses: 1 }
        }
      });

      render(<Leaderboard />);
      
      const matchupsButton = screen.getByText(/Matchup Stats/i);
      fireEvent.click(matchupsButton);

      await waitFor(() => {
        expect(screen.getByText(/BotAlpha vs BotBeta: 3-1/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      (fetch as any).mockRejectedValueOnce(new Error('Network error'));
      
      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to load leaderboard/i)).toBeInTheDocument();
      });

      // Retry button
      const retryButton = screen.getByText(/Retry/i);
      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockLeaderboardServer.getLeaderboard()
      });
      
      fireEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('BotAlpha')).toBeInTheDocument();
      });
    });

    it('should handle empty leaderboard', async () => {
      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => []
      });

      render(<Leaderboard />);
      
      await waitFor(() => {
        expect(screen.getByText(/No battles recorded yet/i)).toBeInTheDocument();
      });
    });
  });
});