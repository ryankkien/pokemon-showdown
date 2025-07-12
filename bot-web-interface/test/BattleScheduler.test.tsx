import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import BattleScheduler from '../src/components/BattleScheduler';
import { LLMPlayer } from '../src/agents/LLMPlayer';

// Mock LLMPlayer
vi.mock('../src/agents/LLMPlayer');

// Mock fetch
global.fetch = vi.fn();

describe('Battle Scheduler', () => {
  let mockBot1: any;
  let mockBot2: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Setup mock bots
    mockBot1 = {
      name: 'TestBot1',
      connect: vi.fn(),
      disconnect: vi.fn(),
      send: vi.fn(),
      onBattleStart: vi.fn(),
      onBattleEnd: vi.fn(),
      isConnected: vi.fn().mockReturnValue(true),
      getCurrentBattle: vi.fn().mockReturnValue(null)
    };

    mockBot2 = {
      name: 'TestBot2',
      connect: vi.fn(),
      disconnect: vi.fn(),
      send: vi.fn(),
      onBattleStart: vi.fn(),
      onBattleEnd: vi.fn(),
      isConnected: vi.fn().mockReturnValue(true),
      getCurrentBattle: vi.fn().mockReturnValue(null)
    };

    (LLMPlayer as any).mockImplementation((name: string) => {
      if (name === 'TestBot1') return mockBot1;
      if (name === 'TestBot2') return mockBot2;
      return {
        name,
        connect: vi.fn(),
        disconnect: vi.fn(),
        send: vi.fn(),
        isConnected: vi.fn().mockReturnValue(true)
      };
    });

    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ success: true })
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Battle Scheduling UI', () => {
    it('should render the battle scheduler component', () => {
      render(<BattleScheduler />);
      
      expect(screen.getByText(/Battle Scheduler/i)).toBeInTheDocument();
      expect(screen.getByText(/Select Bots/i)).toBeInTheDocument();
      expect(screen.getByText(/Start Battle/i)).toBeInTheDocument();
    });

    it('should display bot selection dropdowns', () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2', 'TestBot3']} />);
      
      const selects = screen.getAllByRole('combobox');
      expect(selects).toHaveLength(2); // Bot 1 and Bot 2 selectors
    });

    it('should allow selecting different bots', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2', 'TestBot3']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      expect(bot1Select).toHaveValue('TestBot1');
      expect(bot2Select).toHaveValue('TestBot2');
    });

    it('should prevent selecting the same bot twice', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2', 'TestBot3']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot1' } });
      
      expect(screen.getByText(/Cannot select the same bot twice/i)).toBeInTheDocument();
    });

    it('should display battle format options', () => {
      render(<BattleScheduler />);
      
      expect(screen.getByLabelText(/Battle Format/i)).toBeInTheDocument();
      expect(screen.getByText('Singles')).toBeInTheDocument();
      expect(screen.getByText('Doubles')).toBeInTheDocument();
    });
  });

  describe('Starting Battles', () => {
    it('should start a battle between two bots', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      const startButton = screen.getByText(/Start Battle/i);
      fireEvent.click(startButton);
      
      await waitFor(() => {
        expect(LLMPlayer).toHaveBeenCalledWith('TestBot1', expect.any(String));
        expect(LLMPlayer).toHaveBeenCalledWith('TestBot2', expect.any(String));
        expect(mockBot1.connect).toHaveBeenCalled();
        expect(mockBot2.connect).toHaveBeenCalled();
      });
    });

    it('should create a battle room and join both bots', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      const startButton = screen.getByText(/Start Battle/i);
      fireEvent.click(startButton);
      
      await waitFor(() => {
        // Both bots should join the same room
        expect(mockBot1.send).toHaveBeenCalledWith(expect.stringContaining('/join '));
        expect(mockBot2.send).toHaveBeenCalledWith(expect.stringContaining('/join '));
      });
    });

    it('should handle battle start confirmation', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      const startButton = screen.getByText(/Start Battle/i);
      fireEvent.click(startButton);
      
      // Simulate battle start
      const battleStartCallback = mockBot1.onBattleStart.mock.calls[0][0];
      battleStartCallback('battle-test-123');
      
      await waitFor(() => {
        expect(screen.getByText(/Battle in progress/i)).toBeInTheDocument();
        expect(screen.getByText(/battle-test-123/i)).toBeInTheDocument();
      });
    });

    it('should update status during battle', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      const startButton = screen.getByText(/Start Battle/i);
      fireEvent.click(startButton);
      
      await waitFor(() => {
        expect(screen.getByText(/Waiting for battle to start/i)).toBeInTheDocument();
      });
      
      // Simulate battle progress
      mockBot1.getCurrentBattle.mockReturnValue({ turn: 5, active: true });
      
      await waitFor(() => {
        expect(screen.getByText(/Turn 5/i)).toBeInTheDocument();
      });
    });
  });

  describe('Battle Management', () => {
    it('should allow stopping an ongoing battle', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      // Start battle
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      await waitFor(() => {
        expect(screen.getByText(/Stop Battle/i)).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText(/Stop Battle/i));
      
      expect(mockBot1.disconnect).toHaveBeenCalled();
      expect(mockBot2.disconnect).toHaveBeenCalled();
    });

    it('should handle battle completion', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      // Start battle
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      // Simulate battle end
      const battleEndCallback = mockBot1.onBattleEnd.mock.calls[0][0];
      battleEndCallback({ winner: 'TestBot1', loser: 'TestBot2' });
      
      await waitFor(() => {
        expect(screen.getByText(/Battle Complete/i)).toBeInTheDocument();
        expect(screen.getByText(/Winner: TestBot1/i)).toBeInTheDocument();
      });
      
      // Should update leaderboard
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/battle-result'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('TestBot1')
        })
      );
    });

    it('should handle disconnections during battle', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      // Start battle
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      // Simulate disconnection
      mockBot1.isConnected.mockReturnValue(false);
      
      await waitFor(() => {
        expect(screen.getByText(/TestBot1 disconnected/i)).toBeInTheDocument();
      });
    });
  });

  describe('Battle Queue and Automation', () => {
    it('should queue multiple battles', async () => {
      render(<BattleScheduler bots={['Bot1', 'Bot2', 'Bot3', 'Bot4']} />);
      
      const queueButton = screen.getByText(/Add to Queue/i);
      
      // Add first battle to queue
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'Bot1' } });
      fireEvent.change(bot2Select, { target: { value: 'Bot2' } });
      fireEvent.click(queueButton);
      
      // Add second battle to queue
      fireEvent.change(bot1Select, { target: { value: 'Bot3' } });
      fireEvent.change(bot2Select, { target: { value: 'Bot4' } });
      fireEvent.click(queueButton);
      
      expect(screen.getByText(/Queue: 2 battles/i)).toBeInTheDocument();
    });

    it('should process battle queue automatically', async () => {
      vi.useFakeTimers();
      
      render(<BattleScheduler bots={['Bot1', 'Bot2', 'Bot3', 'Bot4']} autoStart={true} />);
      
      // Add battles to queue
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      const queueButton = screen.getByText(/Add to Queue/i);
      
      fireEvent.change(bot1Select, { target: { value: 'Bot1' } });
      fireEvent.change(bot2Select, { target: { value: 'Bot2' } });
      fireEvent.click(queueButton);
      
      fireEvent.change(bot1Select, { target: { value: 'Bot3' } });
      fireEvent.change(bot2Select, { target: { value: 'Bot4' } });
      fireEvent.click(queueButton);
      
      // Start processing
      fireEvent.click(screen.getByText(/Start Queue/i));
      
      // First battle should start
      await waitFor(() => {
        expect(screen.getByText(/Processing: Bot1 vs Bot2/i)).toBeInTheDocument();
      });
      
      vi.useRealTimers();
    });

    it('should support round-robin tournaments', async () => {
      render(<BattleScheduler bots={['Bot1', 'Bot2', 'Bot3', 'Bot4']} />);
      
      const tournamentButton = screen.getByText(/Round Robin/i);
      fireEvent.click(tournamentButton);
      
      await waitFor(() => {
        // Should create 6 battles (4 choose 2)
        expect(screen.getByText(/6 battles scheduled/i)).toBeInTheDocument();
      });
    });
  });

  describe('Battle Configuration', () => {
    it('should allow setting battle timer', () => {
      render(<BattleScheduler />);
      
      const timerInput = screen.getByLabelText(/Battle Timer/i);
      fireEvent.change(timerInput, { target: { value: '300' } });
      
      expect(timerInput).toHaveValue(300);
    });

    it('should support different battle formats', async () => {
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const formatSelect = screen.getByLabelText(/Battle Format/i);
      fireEvent.change(formatSelect, { target: { value: 'gen9doubles' } });
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      await waitFor(() => {
        expect(mockBot1.send).toHaveBeenCalledWith(expect.stringContaining('gen9doubles'));
      });
    });

    it('should allow custom team selection', () => {
      render(<BattleScheduler />);
      
      const teamCheckbox = screen.getByLabelText(/Use custom teams/i);
      fireEvent.click(teamCheckbox);
      
      expect(screen.getByText(/Team Configuration/i)).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should handle bot connection failures', async () => {
      mockBot1.connect.mockRejectedValue(new Error('Connection failed'));
      
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to connect TestBot1/i)).toBeInTheDocument();
      });
    });

    it('should handle battle creation failures', async () => {
      (fetch as any).mockRejectedValueOnce(new Error('Server error'));
      
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to create battle/i)).toBeInTheDocument();
      });
    });

    it('should retry failed battles', async () => {
      mockBot1.connect.mockRejectedValueOnce(new Error('Temporary failure'));
      mockBot1.connect.mockResolvedValueOnce(undefined);
      
      render(<BattleScheduler bots={['TestBot1', 'TestBot2']} />);
      
      const [bot1Select, bot2Select] = screen.getAllByRole('combobox');
      fireEvent.change(bot1Select, { target: { value: 'TestBot1' } });
      fireEvent.change(bot2Select, { target: { value: 'TestBot2' } });
      
      fireEvent.click(screen.getByText(/Start Battle/i));
      
      await waitFor(() => {
        expect(screen.getByText(/Retry/i)).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByText(/Retry/i));
      
      await waitFor(() => {
        expect(mockBot1.connect).toHaveBeenCalledTimes(2);
      });
    });
  });
});