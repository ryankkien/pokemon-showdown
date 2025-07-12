import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { StateProcessor } from '../src/processors/StateProcessor';
import { LLMClient } from '../src/clients/LLMClient';
import { ResponseParser } from '../src/parsers/ResponseParser';
import { formatState } from '../src/utils/formatState';
import { BattleState, Pokemon } from '../src/types/battle';

// Mock external dependencies
vi.mock('../src/utils/formatState');

describe('Bot Command Processing Pipeline', () => {
  let stateProcessor: StateProcessor;
  let llmClient: LLMClient;
  let responseParser: ResponseParser;

  beforeEach(() => {
    stateProcessor = new StateProcessor();
    llmClient = new LLMClient('test-model', 'test-key');
    responseParser = new ResponseParser();
    
    (formatState as any).mockReturnValue('Formatted battle state');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('StateProcessor', () => {
    it('should extract battle state from request data', () => {
      const requestData = {
        active: [{
          moves: [
            { move: 'Tackle', pp: 35, maxpp: 35 },
            { move: 'Growl', pp: 40, maxpp: 40 }
          ]
        }],
        side: {
          pokemon: [
            { 
              ident: 'p1: Pikachu', 
              details: 'Pikachu, L50',
              condition: '100/100',
              stats: { atk: 100, def: 80, spa: 110, spd: 90, spe: 120 }
            }
          ]
        }
      };

      const battleLogs = ['|switch|p2a: Charmander|Charmander, L50|100/100'];
      
      const state = stateProcessor.extractState(requestData, battleLogs, true);
      
      expect(state.playerTeam).toHaveLength(1);
      expect(state.playerTeam[0].species).toBe('Pikachu');
      expect(state.opponentTeam).toHaveLength(1);
      expect(state.opponentTeam[0].species).toBe('Charmander');
    });

    it('should parse weather conditions from battle logs', () => {
      const requestData = { active: [], side: { pokemon: [] } };
      const battleLogs = [
        '|weather|RainDance',
        '|-weather|RainDance|[upkeep]'
      ];
      
      const state = stateProcessor.extractState(requestData, battleLogs, true);
      
      expect(state.weather).toBe('RainDance');
    });

    it('should parse terrain conditions from battle logs', () => {
      const requestData = { active: [], side: { pokemon: [] } };
      const battleLogs = [
        '|-fieldstart|move: Grassy Terrain'
      ];
      
      const state = stateProcessor.extractState(requestData, battleLogs, true);
      
      expect(state.terrainType).toBe('Grassy Terrain');
    });

    it('should handle status conditions', () => {
      const requestData = {
        side: {
          pokemon: [{
            ident: 'p1: Pikachu',
            details: 'Pikachu, L50',
            condition: '80/100 par',
            stats: { atk: 100, def: 80, spa: 110, spd: 90, spe: 120 }
          }]
        }
      };
      
      const state = stateProcessor.extractState(requestData, [], true);
      
      expect(state.playerTeam[0].status).toBe('par');
      expect(state.playerTeam[0].hpPercentage).toBe(80);
    });

    it('should extract field effects from battle logs', () => {
      const requestData = { active: [], side: { pokemon: [] } };
      const battleLogs = [
        '|-sidestart|p1: player|move: Stealth Rock',
        '|-sidestart|p2: opponent|Spikes'
      ];
      
      const state = stateProcessor.extractState(requestData, battleLogs, true);
      
      expect(state.fieldEffects).toContain('p1: Stealth Rock');
      expect(state.fieldEffects).toContain('p2: Spikes');
    });
  });

  describe('LLMClient', () => {
    it('should format and send battle state to LLM', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ 
          choices: [{ message: { content: 'switch 2' } }] 
        })
      });
      global.fetch = mockFetch;

      const battleState: BattleState = {
        turn: 1,
        playerTeam: [],
        opponentTeam: [],
        weather: null,
        terrainType: null,
        isP1: true,
        fieldEffects: []
      };

      const result = await llmClient.getAction(battleState, ['move 1', 'switch 2']);
      
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-key'
          })
        })
      );
      
      expect(result).toBe('switch 2');
    });

    it('should retry on LLM failure', async () => {
      const mockFetch = vi.fn()
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ 
            choices: [{ message: { content: 'move 1' } }] 
          })
        });
      global.fetch = mockFetch;

      const battleState: BattleState = {
        turn: 1,
        playerTeam: [],
        opponentTeam: [],
        weather: null,
        terrainType: null,
        isP1: true,
        fieldEffects: []
      };

      const result = await llmClient.getAction(battleState, ['move 1']);
      
      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(result).toBe('move 1');
    });

    it('should fall back to default action after max retries', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      global.fetch = mockFetch;

      const battleState: BattleState = {
        turn: 1,
        playerTeam: [],
        opponentTeam: [],
        weather: null,
        terrainType: null,
        isP1: true,
        fieldEffects: []
      };

      const result = await llmClient.getAction(battleState, ['move 1', 'move 2']);
      
      expect(mockFetch).toHaveBeenCalledTimes(3); // 3 retries
      expect(result).toBe('move 1'); // Falls back to first available action
    });
  });

  describe('ResponseParser', () => {
    it('should parse move commands', () => {
      const choices = ['move 1', 'move 2', 'move 3'];
      
      expect(responseParser.parseChoice('Use Tackle', choices)).toBe('move 1');
      expect(responseParser.parseChoice('move 2', choices)).toBe('move 2');
      expect(responseParser.parseChoice('I choose move 3!', choices)).toBe('move 3');
    });

    it('should parse switch commands', () => {
      const choices = ['move 1', 'switch 2', 'switch 3'];
      
      expect(responseParser.parseChoice('Switch to Pokemon 2', choices)).toBe('switch 2');
      expect(responseParser.parseChoice('switch 3', choices)).toBe('switch 3');
      expect(responseParser.parseChoice('Send out the third Pokemon', choices)).toBe('switch 3');
    });

    it('should handle ambiguous commands', () => {
      const choices = ['move 1', 'move 2'];
      
      // Should default to first choice if can't parse
      expect(responseParser.parseChoice('Do something!', choices)).toBe('move 1');
      expect(responseParser.parseChoice('', choices)).toBe('move 1');
    });

    it('should parse team order commands', () => {
      const teamChoices = ['team 123456', 'team 234561', 'team 345612'];
      
      expect(responseParser.parseChoice('team 234561', teamChoices)).toBe('team 234561');
      expect(responseParser.parseChoice('Use team order: 3,4,5,6,1,2', teamChoices)).toBe('team 345612');
    });

    it('should handle complex move descriptions', () => {
      const choices = ['move 1', 'move 2', 'move 3', 'move 4'];
      
      expect(responseParser.parseChoice('Use the first move to attack', choices)).toBe('move 1');
      expect(responseParser.parseChoice('Let\'s go with option 2', choices)).toBe('move 2');
      expect(responseParser.parseChoice('Execute move number four', choices)).toBe('move 4');
    });

    it('should validate parsed choice against available options', () => {
      const choices = ['move 1', 'move 2'];
      
      // Trying to select unavailable option should default to first
      expect(responseParser.parseChoice('move 3', choices)).toBe('move 1');
      expect(responseParser.parseChoice('switch 5', choices)).toBe('move 1');
    });
  });

  describe('Full Command Pipeline', () => {
    it('should process battle state through entire pipeline', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ 
          choices: [{ message: { content: 'I think we should switch to Pokemon 2' } }] 
        })
      });
      global.fetch = mockFetch;

      // Setup request data
      const requestData = {
        active: [{ moves: [{ move: 'Tackle' }] }],
        side: { pokemon: [{ ident: 'p1: Pikachu', details: 'Pikachu', condition: '100/100' }] }
      };
      
      // Process through pipeline
      const state = stateProcessor.extractState(requestData, [], true);
      const llmResponse = await llmClient.getAction(state, ['move 1', 'switch 2']);
      const finalChoice = responseParser.parseChoice(llmResponse, ['move 1', 'switch 2']);
      
      expect(finalChoice).toBe('switch 2');
    });

    it('should handle forced switches', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ 
          choices: [{ message: { content: 'switch 3' } }] 
        })
      });
      global.fetch = mockFetch;

      const forceSwitch = true;
      const choices = ['switch 2', 'switch 3', 'switch 4'];
      
      const state: BattleState = {
        turn: 5,
        playerTeam: [],
        opponentTeam: [],
        weather: null,
        terrainType: null,
        isP1: true,
        fieldEffects: []
      };
      
      const result = await llmClient.getAction(state, choices);
      const parsed = responseParser.parseChoice(result, choices);
      
      expect(parsed).toMatch(/^switch \d$/);
    });
  });
});