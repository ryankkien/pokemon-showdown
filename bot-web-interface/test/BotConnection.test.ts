import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import WebSocket from 'ws';
import { LLMPlayer } from '../src/agents/LLMPlayer';
import { StateProcessor } from '../src/processors/StateProcessor';
import { LLMClient } from '../src/clients/LLMClient';
import { ResponseParser } from '../src/parsers/ResponseParser';

// Mock WebSocket
vi.mock('ws');

// Mock dependencies
vi.mock('../src/processors/StateProcessor');
vi.mock('../src/clients/LLMClient');
vi.mock('../src/parsers/ResponseParser');

describe('Bot Connection and WebSocket Handling', () => {
  let mockWebSocket: any;
  let player: LLMPlayer;
  let mockStateProcessor: any;
  let mockLLMClient: any;
  let mockResponseParser: any;

  beforeEach(() => {
    // Setup WebSocket mock
    mockWebSocket = {
      on: vi.fn(),
      send: vi.fn(),
      close: vi.fn(),
      readyState: WebSocket.OPEN,
      OPEN: WebSocket.OPEN,
      CLOSED: WebSocket.CLOSED,
      CONNECTING: WebSocket.CONNECTING,
      CLOSING: WebSocket.CLOSING
    };

    (WebSocket as any).mockImplementation(() => mockWebSocket);

    // Setup other mocks
    mockStateProcessor = {
      extractState: vi.fn().mockReturnValue({
        turn: 1,
        playerTeam: [],
        opponentTeam: [],
        weather: null,
        terrainType: null,
        isP1: true
      })
    };

    mockLLMClient = {
      getAction: vi.fn().mockResolvedValue('switch 2')
    };

    mockResponseParser = {
      parseChoice: vi.fn().mockReturnValue('switch 2')
    };

    (StateProcessor as any).mockImplementation(() => mockStateProcessor);
    (LLMClient as any).mockImplementation(() => mockLLMClient);
    (ResponseParser as any).mockImplementation(() => mockResponseParser);

    player = new LLMPlayer('test-bot', 'test-room');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should establish WebSocket connection to Pokemon Showdown server', () => {
    expect(WebSocket).toHaveBeenCalledWith('ws://sim3.psim.us:8000/showdown/websocket');
    expect(mockWebSocket.on).toHaveBeenCalledWith('open', expect.any(Function));
    expect(mockWebSocket.on).toHaveBeenCalledWith('message', expect.any(Function));
    expect(mockWebSocket.on).toHaveBeenCalledWith('error', expect.any(Function));
    expect(mockWebSocket.on).toHaveBeenCalledWith('close', expect.any(Function));
  });

  it('should handle connection open event', () => {
    const openHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'open')[1];
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    
    openHandler();
    
    expect(consoleSpy).toHaveBeenCalledWith('[test-bot] Connected to Pokemon Showdown');
    consoleSpy.mockRestore();
  });

  it('should handle connection error event', () => {
    const errorHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'error')[1];
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const testError = new Error('Connection failed');
    
    errorHandler(testError);
    
    expect(consoleSpy).toHaveBeenCalledWith('[test-bot] WebSocket error:', testError);
    consoleSpy.mockRestore();
  });

  it('should handle connection close event', () => {
    const closeHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'close')[1];
    const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    
    closeHandler();
    
    expect(consoleSpy).toHaveBeenCalledWith('[test-bot] Disconnected from Pokemon Showdown');
    consoleSpy.mockRestore();
  });

  it('should process incoming messages', () => {
    const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
    
    const testMessage = Buffer.from('>test-room\n|request|{"active":[{"moves":[{"move":"Tackle"}]}]}');
    messageHandler(testMessage);
    
    expect(mockStateProcessor.extractState).toHaveBeenCalled();
  });

  it('should handle challstr for authentication', () => {
    const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
    
    const challstrMessage = Buffer.from('|challstr|CHALLSTR123');
    messageHandler(challstrMessage);
    
    // Should attempt to login
    expect(mockWebSocket.send).toHaveBeenCalledWith(expect.stringContaining('|/trn test-bot,0,'));
  });

  it('should join room after successful login', () => {
    const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
    
    const updateUserMessage = Buffer.from('|updateuser|test-bot|1|avatar');
    messageHandler(updateUserMessage);
    
    expect(mockWebSocket.send).toHaveBeenCalledWith('|/join test-room');
  });

  it('should send messages through WebSocket', () => {
    player.send('test message');
    
    expect(mockWebSocket.send).toHaveBeenCalledWith('test message');
  });

  it('should handle WebSocket reconnection', async () => {
    // Simulate connection close
    mockWebSocket.readyState = WebSocket.CLOSED;
    
    // Trigger reconnection attempt
    const closeHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'close')[1];
    closeHandler();
    
    // Wait for reconnection delay
    await new Promise(resolve => setTimeout(resolve, 3100));
    
    // Should create new WebSocket connection
    expect(WebSocket).toHaveBeenCalledTimes(2);
  });

  it('should queue messages when WebSocket is not ready', () => {
    mockWebSocket.readyState = WebSocket.CONNECTING;
    
    player.send('queued message');
    
    // Message should not be sent immediately
    expect(mockWebSocket.send).not.toHaveBeenCalled();
    
    // Simulate connection open
    mockWebSocket.readyState = WebSocket.OPEN;
    const openHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'open')[1];
    openHandler();
    
    // Queued message should be sent
    expect(mockWebSocket.send).toHaveBeenCalledWith('queued message');
  });

  it('should handle multiple simultaneous bot connections', () => {
    const bot1 = new LLMPlayer('bot1', 'room1');
    const bot2 = new LLMPlayer('bot2', 'room2');
    
    expect(WebSocket).toHaveBeenCalledTimes(3); // Original + 2 new bots
    
    // Each bot should have its own WebSocket connection
    expect(mockWebSocket.on).toHaveBeenCalledTimes(12); // 4 events × 3 bots
  });

  it('should properly close WebSocket connection', () => {
    player.disconnect();
    
    expect(mockWebSocket.close).toHaveBeenCalled();
  });

  it('should handle malformed messages gracefully', () => {
    const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    // Send malformed message
    messageHandler(Buffer.from('malformed|message|without|proper|format'));
    
    // Should not crash
    expect(consoleSpy).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });
});