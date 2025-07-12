import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import App from '../src/App';
import { LLMPlayer } from '../src/agents/LLMPlayer';
import WebSocket from 'ws';

// Mock all external dependencies
vi.mock('ws');
vi.mock('../src/agents/LLMPlayer');
vi.mock('../src/services/LeaderboardServer');
vi.mock('../src/services/BattleRelayServer');

// Mock fetch globally
global.fetch = vi.fn();

describe('Integration Tests - Full Battle Flow', () => {
  let mockWebSocket: any;
  let mockBot1: any;
  let mockBot2: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock WebSocket
    mockWebSocket = {
      on: vi.fn(),
      send: vi.fn(),
      close: vi.fn(),
      readyState: WebSocket.OPEN,
      OPEN: WebSocket.OPEN
    };

    (WebSocket as any).mockImplementation(() => mockWebSocket);

    // Mock bots
    mockBot1 = {
      name: 'IntegrationBot1',
      connect: vi.fn().mockResolvedValue(undefined),
      disconnect: vi.fn(),
      send: vi.fn(),
      onBattleStart: vi.fn(),
      onBattleEnd: vi.fn(),
      onRequest: vi.fn(),
      isConnected: vi.fn().mockReturnValue(true),
      getCurrentBattle: vi.fn().mockReturnValue(null),
      getState: vi.fn().mockReturnValue(null)
    };

    mockBot2 = {
      name: 'IntegrationBot2',
      connect: vi.fn().mockResolvedValue(undefined),
      disconnect: vi.fn(),
      send: vi.fn(),
      onBattleStart: vi.fn(),
      onBattleEnd: vi.fn(),
      onRequest: vi.fn(),
      isConnected: vi.fn().mockReturnValue(true),
      getCurrentBattle: vi.fn().mockReturnValue(null),
      getState: vi.fn().mockReturnValue(null)
    };

    (LLMPlayer as any).mockImplementation((name: string) => {
      if (name === 'IntegrationBot1') return mockBot1;
      if (name === 'IntegrationBot2') return mockBot2;
      return mockBot1;
    });

    // Mock fetch responses
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Complete Battle Workflow', () => {
    it('should complete a full battle from start to finish', async () => {
      render(<App />);
      
      // Step 1: Navigate to Battle Scheduler
      const battleSchedulerBtn = screen.getByText('Battle Scheduler');
      fireEvent.click(battleSchedulerBtn);
      
      await waitFor(() => {
        expect(screen.getByText(/Select Bots/i)).toBeInTheDocument();
      });

      // Step 2: Select bots and start battle
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'IntegrationBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'IntegrationBot2' } });
      
      const startButton = screen.getByText(/Start Battle/i);
      fireEvent.click(startButton);

      // Step 3: Verify bot connections
      await waitFor(() => {
        expect(mockBot1.connect).toHaveBeenCalled();
        expect(mockBot2.connect).toHaveBeenCalled();
      });

      // Step 4: Simulate battle initialization
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      
      // Send challstr to both bots
      messageHandler(Buffer.from('|challstr|CHALLSTR123'));
      
      // Verify login attempts
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        expect.stringContaining('|/trn IntegrationBot1')
      );

      // Step 5: Simulate room creation and joining
      messageHandler(Buffer.from('|updateuser|IntegrationBot1|1|avatar'));
      messageHandler(Buffer.from('|updateuser|IntegrationBot2|1|avatar'));
      
      // Both bots should join the battle room
      expect(mockWebSocket.send).toHaveBeenCalledWith(expect.stringContaining('|/join '));

      // Step 6: Start the battle
      const battleId = 'battle-gen9ou-integration123';
      const battleStartHandler = mockBot1.onBattleStart.mock.calls[0][0];
      battleStartHandler(battleId);

      // Step 7: Simulate battle turns
      const battleState = {
        request: {
          active: [{ moves: [{ move: 'Tackle', pp: 35 }] }],
          side: { pokemon: [{ ident: 'p1: Pikachu', condition: '100/100' }] }
        }
      };

      // Trigger move request
      const requestHandler = mockBot1.onRequest.mock.calls[0][0];
      requestHandler(battleState);

      // Bot should make a move
      await waitFor(() => {
        expect(mockBot1.send).toHaveBeenCalledWith(expect.stringContaining('|/choose'));
      });

      // Step 8: Navigate to Live Battle view
      fireEvent.click(screen.getByText('Live Battle'));
      
      await waitFor(() => {
        expect(screen.getByTestId('live-battle-view')).toBeInTheDocument();
      });

      // Step 9: Simulate battle completion
      const battleEndHandler = mockBot1.onBattleEnd.mock.calls[0][0];
      battleEndHandler({ 
        winner: 'IntegrationBot1', 
        loser: 'IntegrationBot2',
        replay: 'https://replay.pokemonshowdown.com/' + battleId
      });

      // Step 10: Check leaderboard update
      fireEvent.click(screen.getByText('Leaderboard'));
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/battle-result'),
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('IntegrationBot1')
          })
        );
      });
    });

    it('should handle multiple concurrent battles', async () => {
      render(<App />);
      
      // Navigate to scheduler
      fireEvent.click(screen.getByText('Battle Scheduler'));
      
      // Create multiple bot instances
      const bots = ['Bot1', 'Bot2', 'Bot3', 'Bot4'];
      
      // Queue multiple battles
      const queueButton = screen.getByText(/Add to Queue/i);
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      
      // Battle 1: Bot1 vs Bot2
      fireEvent.change(bot1Select, { target: { value: 'Bot1' } });
      fireEvent.change(bot2Select, { target: { value: 'Bot2' } });
      fireEvent.click(queueButton);
      
      // Battle 2: Bot3 vs Bot4
      fireEvent.change(bot1Select, { target: { value: 'Bot3' } });
      fireEvent.change(bot2Select, { target: { value: 'Bot4' } });
      fireEvent.click(queueButton);
      
      // Start queue processing
      fireEvent.click(screen.getByText(/Start Queue/i));
      
      await waitFor(() => {
        expect(LLMPlayer).toHaveBeenCalledTimes(4); // 4 bots created
      });
    });
  });

  describe('Error Recovery and Edge Cases', () => {
    it('should recover from disconnection during battle', async () => {
      render(<App />);
      
      // Start a battle
      fireEvent.click(screen.getByText('Battle Scheduler'));
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'IntegrationBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'IntegrationBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      await waitFor(() => {
        expect(mockBot1.connect).toHaveBeenCalled();
      });

      // Simulate disconnection
      mockBot1.isConnected.mockReturnValue(false);
      const closeHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'close')[1];
      closeHandler();

      // Should attempt reconnection
      await waitFor(() => {
        expect(mockBot1.connect).toHaveBeenCalledTimes(2);
      }, { timeout: 5000 });
    });

    it('should handle invalid battle commands gracefully', async () => {
      render(<App />);
      
      // Setup battle
      fireEvent.click(screen.getByText('Battle Scheduler'));
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'IntegrationBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'IntegrationBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));

      // Send invalid command
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      messageHandler(Buffer.from('|error|[Invalid choice] Can\'t switch: The active Pokémon is trapped'));

      // Bot should retry with a different action
      await waitFor(() => {
        expect(mockBot1.send).toHaveBeenCalledTimes(2);
      });
    });

    it('should handle team preview phase', async () => {
      render(<App />);
      
      // Start battle
      fireEvent.click(screen.getByText('Battle Scheduler'));
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'IntegrationBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'IntegrationBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));

      // Simulate team preview request
      const teamPreviewRequest = {
        teamPreview: true,
        side: {
          pokemon: [
            { ident: 'p1: Pikachu' },
            { ident: 'p1: Charizard' },
            { ident: 'p1: Blastoise' },
            { ident: 'p1: Venusaur' },
            { ident: 'p1: Snorlax' },
            { ident: 'p1: Lapras' }
          ]
        }
      };

      const requestHandler = mockBot1.onRequest.mock.calls[0][0];
      requestHandler(teamPreviewRequest);

      // Bot should send team order
      await waitFor(() => {
        expect(mockBot1.send).toHaveBeenCalledWith(
          expect.stringMatching(/\|\/team \d+/)
        );
      });
    });
  });

  describe('Real-time Updates and Synchronization', () => {
    it('should sync battle state across all views', async () => {
      render(<App />);
      
      // Start battle
      fireEvent.click(screen.getByText('Battle Scheduler'));
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'IntegrationBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'IntegrationBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));

      const battleId = 'battle-test-sync';
      const battleStartHandler = mockBot1.onBattleStart.mock.calls[0][0];
      battleStartHandler(battleId);

      // Switch to Live Battle view
      fireEvent.click(screen.getByText('Live Battle'));

      // Update battle state
      mockBot1.getState.mockReturnValue({
        turn: 5,
        playerTeam: [{ species: 'Pikachu', hp: 80, maxHp: 100 }],
        opponentTeam: [{ species: 'Charizard', hp: 120, maxHp: 150 }]
      });

      // Trigger state update
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      messageHandler(Buffer.from(`>battle-${battleId}\n|turn|5`));

      await waitFor(() => {
        expect(screen.getByText(/Turn 5/i)).toBeInTheDocument();
      });

      // Switch to Showdown view
      fireEvent.click(screen.getByText('Showdown Battle'));
      
      const iframe = screen.getByTitle('Pokemon Showdown Battle');
      expect(iframe).toHaveAttribute('src', expect.stringContaining(battleId));
    });

    it('should update leaderboard in real-time', async () => {
      render(<App />);
      
      // Navigate to leaderboard
      fireEvent.click(screen.getByText('Leaderboard'));
      
      // Mock initial leaderboard data
      (fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => [
          { name: 'IntegrationBot1', wins: 5, losses: 2 },
          { name: 'IntegrationBot2', wins: 3, losses: 4 }
        ]
      });

      await waitFor(() => {
        expect(screen.getByText('5-2')).toBeInTheDocument();
      });

      // Simulate WebSocket update for battle completion
      const ws = new WebSocket('ws://localhost:5001');
      const wsMessageHandler = (ws as any).addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )[1];

      wsMessageHandler({
        data: JSON.stringify({
          type: 'battle-complete',
          winner: 'IntegrationBot1',
          loser: 'IntegrationBot2',
          updates: [
            { name: 'IntegrationBot1', wins: 6, losses: 2 },
            { name: 'IntegrationBot2', wins: 3, losses: 5 }
          ]
        })
      });

      // Leaderboard should update without refresh
      await waitFor(() => {
        expect(screen.getByText('6-2')).toBeInTheDocument();
        expect(screen.getByText('3-5')).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Load Testing', () => {
    it('should handle rapid battle starts and stops', async () => {
      render(<App />);
      
      fireEvent.click(screen.getByText('Battle Scheduler'));
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      const startButton = screen.getByText(/Start Battle/i);
      
      // Rapidly start and stop battles
      for (let i = 0; i < 5; i++) {
        fireEvent.change(bot1Select, { target: { value: 'IntegrationBot1' } });
        fireEvent.change(bot2Select, { target: { value: 'IntegrationBot2' } });
        fireEvent.click(startButton);
        
        await waitFor(() => {
          expect(screen.getByText(/Stop Battle/i)).toBeInTheDocument();
        });
        
        fireEvent.click(screen.getByText(/Stop Battle/i));
        
        await waitFor(() => {
          expect(screen.getByText(/Start Battle/i)).toBeInTheDocument();
        });
      }

      // All connections should be properly cleaned up
      expect(mockBot1.disconnect).toHaveBeenCalledTimes(5);
      expect(mockBot2.disconnect).toHaveBeenCalledTimes(5);
    });

    it('should maintain performance with many active battles', async () => {
      render(<App />);
      
      const startTime = Date.now();
      
      // Create 10 concurrent battles
      for (let i = 0; i < 10; i++) {
        const bot1 = new LLMPlayer(`PerfBot${i * 2}`, `room${i}`);
        const bot2 = new LLMPlayer(`PerfBot${i * 2 + 1}`, `room${i}`);
      }

      const endTime = Date.now();
      
      // Should complete within reasonable time
      expect(endTime - startTime).toBeLessThan(1000);
    });
  });
});