import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import LiveBattle from '../src/components/LiveBattle';
import ShowdownBattle from '../src/components/ShowdownBattle';
import { BattleState } from '../src/types/battle';

// Mock WebSocket
global.WebSocket = vi.fn(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  send: vi.fn(),
  close: vi.fn(),
  readyState: 1
})) as any;

describe('Battle Visualization Components', () => {
  describe('LiveBattle Component', () => {
    const mockBattleState: BattleState = {
      turn: 5,
      playerTeam: [
        {
          species: 'Pikachu',
          level: 50,
          hp: 80,
          maxHp: 100,
          hpPercentage: 80,
          status: null,
          isActive: true,
          stats: { atk: 100, def: 80, spa: 110, spd: 90, spe: 120 },
          moves: ['Thunderbolt', 'Quick Attack', 'Iron Tail', 'Thunder Wave'],
          ability: 'Static',
          item: 'Light Ball'
        },
        {
          species: 'Charizard',
          level: 50,
          hp: 150,
          maxHp: 150,
          hpPercentage: 100,
          status: null,
          isActive: false,
          stats: { atk: 120, def: 90, spa: 130, spd: 100, spe: 110 },
          moves: ['Flamethrower', 'Dragon Claw', 'Earthquake', 'Roost'],
          ability: 'Blaze',
          item: 'Charizardite X'
        }
      ],
      opponentTeam: [
        {
          species: 'Blastoise',
          level: 50,
          hp: 60,
          maxHp: 150,
          hpPercentage: 40,
          status: 'brn',
          isActive: true,
          stats: { atk: 90, def: 120, spa: 125, spd: 110, spe: 85 },
          moves: ['Hydro Pump', 'Ice Beam', 'Earthquake', 'Shell Smash'],
          ability: 'Torrent',
          item: 'Leftovers'
        }
      ],
      weather: 'RainDance',
      terrainType: null,
      isP1: true,
      fieldEffects: ['p1: Stealth Rock', 'p2: Spikes']
    };

    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should render the live battle component', () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      expect(screen.getByText(/Turn 5/i)).toBeInTheDocument();
      expect(screen.getByText('Pikachu')).toBeInTheDocument();
      expect(screen.getByText('Blastoise')).toBeInTheDocument();
    });

    it('should display Pokemon HP bars', () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      const pikachuHP = screen.getByText('80/100');
      const blastoiseHP = screen.getByText('60/150');
      
      expect(pikachuHP).toBeInTheDocument();
      expect(blastoiseHP).toBeInTheDocument();
    });

    it('should show status conditions', () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      expect(screen.getByText('BRN')).toBeInTheDocument(); // Blastoise burn status
    });

    it('should display weather effects', () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      expect(screen.getByText(/Rain/i)).toBeInTheDocument();
    });

    it('should show field effects', () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      expect(screen.getByText(/Stealth Rock/i)).toBeInTheDocument();
      expect(screen.getByText(/Spikes/i)).toBeInTheDocument();
    });

    it('should update when battle state changes', () => {
      const { rerender } = render(<LiveBattle battleState={mockBattleState} />);
      
      const updatedState = {
        ...mockBattleState,
        turn: 6,
        playerTeam: [{
          ...mockBattleState.playerTeam[0],
          hp: 60,
          hpPercentage: 60
        }]
      };
      
      rerender(<LiveBattle battleState={updatedState} />);
      
      expect(screen.getByText(/Turn 6/i)).toBeInTheDocument();
      expect(screen.getByText('60/100')).toBeInTheDocument();
    });

    it('should display team preview', () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      // Check for team members
      expect(screen.getByText('Charizard')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument(); // Charizard's HP
    });

    it('should show move animations placeholder', () => {
      render(<LiveBattle battleState={mockBattleState} lastMove="Thunderbolt" />);
      
      expect(screen.getByText(/Thunderbolt/i)).toBeInTheDocument();
    });

    it('should handle empty battle state', () => {
      const emptyState: BattleState = {
        turn: 0,
        playerTeam: [],
        opponentTeam: [],
        weather: null,
        terrainType: null,
        isP1: true,
        fieldEffects: []
      };
      
      render(<LiveBattle battleState={emptyState} />);
      
      expect(screen.getByText(/Battle not started yet/i)).toBeInTheDocument();
    });

    it('should connect to battle relay WebSocket', () => {
      render(<LiveBattle battleState={mockBattleState} battleId="test-battle" />);
      
      expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:5001');
    });
  });

  describe('ShowdownBattle Component', () => {
    it('should render iframe with correct URL', () => {
      render(<ShowdownBattle battleId="battle-gen9ou-123456" />);
      
      const iframe = screen.getByTitle('Pokemon Showdown Battle');
      expect(iframe).toHaveAttribute('src', 'https://play.pokemonshowdown.com/battle-gen9ou-123456');
    });

    it('should update iframe src when battle ID changes', () => {
      const { rerender } = render(<ShowdownBattle battleId="battle-gen9ou-123456" />);
      
      let iframe = screen.getByTitle('Pokemon Showdown Battle');
      expect(iframe).toHaveAttribute('src', 'https://play.pokemonshowdown.com/battle-gen9ou-123456');
      
      rerender(<ShowdownBattle battleId="battle-gen9ou-789012" />);
      
      iframe = screen.getByTitle('Pokemon Showdown Battle');
      expect(iframe).toHaveAttribute('src', 'https://play.pokemonshowdown.com/battle-gen9ou-789012');
    });

    it('should display message when no battle ID provided', () => {
      render(<ShowdownBattle />);
      
      expect(screen.getByText(/No battle ID provided/i)).toBeInTheDocument();
    });

    it('should have proper iframe attributes', () => {
      render(<ShowdownBattle battleId="test-battle" />);
      
      const iframe = screen.getByTitle('Pokemon Showdown Battle');
      expect(iframe).toHaveAttribute('width', '100%');
      expect(iframe).toHaveAttribute('height', '600');
      expect(iframe).toHaveAttribute('frameBorder', '0');
    });
  });

  describe('Battle Animation and Updates', () => {
    it('should animate HP bar changes', async () => {
      const { rerender } = render(<LiveBattle battleState={mockBattleState} />);
      
      // Update HP
      const updatedState = {
        ...mockBattleState,
        playerTeam: [{
          ...mockBattleState.playerTeam[0],
          hp: 50,
          hpPercentage: 50
        }]
      };
      
      rerender(<LiveBattle battleState={updatedState} />);
      
      // Check for animation class or transition
      const hpBar = screen.getByTestId('hp-bar-Pikachu');
      expect(hpBar).toHaveStyle({ width: '50%' });
    });

    it('should display critical hit indicators', () => {
      render(<LiveBattle 
        battleState={mockBattleState} 
        lastMove="Thunderbolt"
        wasCritical={true}
      />);
      
      expect(screen.getByText(/Critical Hit!/i)).toBeInTheDocument();
    });

    it('should show effectiveness messages', () => {
      render(<LiveBattle 
        battleState={mockBattleState} 
        lastMove="Thunderbolt"
        effectiveness="super effective"
      />);
      
      expect(screen.getByText(/It's super effective!/i)).toBeInTheDocument();
    });
  });

  describe('Interactive Elements', () => {
    it('should display speed order indicator', () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      // Pikachu (120 speed) should be shown as faster than Blastoise (85 speed)
      const speedIndicator = screen.getByTestId('speed-indicator');
      expect(speedIndicator).toHaveTextContent(/Pikachu moves first/i);
    });

    it('should show type effectiveness preview on hover', async () => {
      render(<LiveBattle battleState={mockBattleState} />);
      
      const thunderboltMove = screen.getByText('Thunderbolt');
      fireEvent.mouseEnter(thunderboltMove);
      
      await waitFor(() => {
        expect(screen.getByText(/Super effective against Blastoise/i)).toBeInTheDocument();
      });
    });

    it('should display stat changes', () => {
      const stateWithBoosts = {
        ...mockBattleState,
        playerTeam: [{
          ...mockBattleState.playerTeam[0],
          boosts: { atk: 2, def: -1, spa: 0, spd: 0, spe: 1 }
        }]
      };
      
      render(<LiveBattle battleState={stateWithBoosts} />);
      
      expect(screen.getByText(/Attack \+2/i)).toBeInTheDocument();
      expect(screen.getByText(/Defense -1/i)).toBeInTheDocument();
      expect(screen.getByText(/Speed \+1/i)).toBeInTheDocument();
    });
  });
});