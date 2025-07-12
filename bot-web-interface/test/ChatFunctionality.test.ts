import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import WebSocket from 'ws';
import { LLMPlayer } from '../src/agents/LLMPlayer';

// Mock WebSocket
vi.mock('ws');

describe('Chat Functionality', () => {
  let mockWebSocket: any;
  let player: LLMPlayer;

  beforeEach(() => {
    // Setup WebSocket mock
    mockWebSocket = {
      on: vi.fn(),
      send: vi.fn(),
      close: vi.fn(),
      readyState: WebSocket.OPEN,
      OPEN: WebSocket.OPEN
    };

    (WebSocket as any).mockImplementation(() => mockWebSocket);

    player = new LLMPlayer('test-bot', 'test-room');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Sending Chat Messages', () => {
    it('should send chat messages to the room', () => {
      player.sendChatMessage('Hello everyone!');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('test-room|Hello everyone!');
    });

    it('should handle multi-line chat messages', () => {
      player.sendChatMessage('Line 1\nLine 2\nLine 3');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('test-room|Line 1\nLine 2\nLine 3');
    });

    it('should escape special characters in chat', () => {
      player.sendChatMessage('Test | message & symbols < >');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('test-room|Test | message & symbols < >');
    });

    it('should handle empty chat messages', () => {
      player.sendChatMessage('');
      
      // Should not send empty messages
      expect(mockWebSocket.send).not.toHaveBeenCalled();
    });

    it('should trim whitespace from chat messages', () => {
      player.sendChatMessage('  Hello World  ');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('test-room|Hello World');
    });
  });

  describe('Receiving Chat Messages', () => {
    it('should parse incoming chat messages', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      const chatCallback = vi.fn();
      
      player.onChatMessage(chatCallback);
      
      const chatMessage = Buffer.from('>test-room\n|c|TestUser|Hello bot!');
      messageHandler(chatMessage);
      
      expect(chatCallback).toHaveBeenCalledWith({
        user: 'TestUser',
        message: 'Hello bot!',
        room: 'test-room'
      });
    });

    it('should handle chat messages with timestamps', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      const chatCallback = vi.fn();
      
      player.onChatMessage(chatCallback);
      
      const chatMessage = Buffer.from('>test-room\n|c:|1234567890|TestUser|Message with timestamp');
      messageHandler(chatMessage);
      
      expect(chatCallback).toHaveBeenCalledWith({
        user: 'TestUser',
        message: 'Message with timestamp',
        room: 'test-room',
        timestamp: 1234567890
      });
    });

    it('should ignore non-chat messages', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      const chatCallback = vi.fn();
      
      player.onChatMessage(chatCallback);
      
      const nonChatMessage = Buffer.from('>test-room\n|request|{"active":[]}');
      messageHandler(nonChatMessage);
      
      expect(chatCallback).not.toHaveBeenCalled();
    });

    it('should handle system messages', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      const chatCallback = vi.fn();
      
      player.onChatMessage(chatCallback);
      
      const systemMessage = Buffer.from('>test-room\n|raw|<div>System announcement</div>');
      messageHandler(systemMessage);
      
      expect(chatCallback).toHaveBeenCalledWith({
        user: 'System',
        message: '<div>System announcement</div>',
        room: 'test-room',
        isRaw: true
      });
    });
  });

  describe('Chat Commands', () => {
    it('should respond to direct mentions', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      
      player.enableAutoResponse(true);
      
      const mentionMessage = Buffer.from('>test-room\n|c|User|@test-bot help');
      messageHandler(mentionMessage);
      
      // Should send a response
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        expect.stringContaining('test-room|')
      );
    });

    it('should handle whisper messages', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      const whisperCallback = vi.fn();
      
      player.onWhisper(whisperCallback);
      
      const whisperMessage = Buffer.from('|pm|TestUser|test-bot|Private message');
      messageHandler(whisperMessage);
      
      expect(whisperCallback).toHaveBeenCalledWith({
        from: 'TestUser',
        to: 'test-bot',
        message: 'Private message'
      });
    });

    it('should send whisper responses', () => {
      player.sendWhisper('TestUser', 'Thanks for the message!');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('|/w TestUser, Thanks for the message!');
    });

    it('should handle chat rate limiting', async () => {
      const messages = ['Message 1', 'Message 2', 'Message 3', 'Message 4', 'Message 5'];
      
      // Send multiple messages rapidly
      messages.forEach(msg => player.sendChatMessage(msg));
      
      // First 3 should send immediately
      expect(mockWebSocket.send).toHaveBeenCalledTimes(3);
      
      // Rest should be queued
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Additional messages should have been sent with delay
      expect(mockWebSocket.send).toHaveBeenCalledTimes(5);
    });
  });

  describe('Room Management', () => {
    it('should join multiple rooms', () => {
      player.joinRoom('lobby');
      player.joinRoom('battles');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('|/join lobby');
      expect(mockWebSocket.send).toHaveBeenCalledWith('|/join battles');
    });

    it('should leave rooms', () => {
      player.leaveRoom('test-room');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('|/leave test-room');
    });

    it('should track active rooms', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      
      // Simulate joining rooms
      messageHandler(Buffer.from('|init|chat'));
      messageHandler(Buffer.from('>lobby'));
      messageHandler(Buffer.from('>battles'));
      
      expect(player.getActiveRooms()).toContain('lobby');
      expect(player.getActiveRooms()).toContain('battles');
    });
  });

  describe('Message Formatting', () => {
    it('should support markdown-style formatting', () => {
      player.sendChatMessage('**bold** and *italic* text');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('test-room|**bold** and *italic* text');
    });

    it('should handle Unicode and emojis', () => {
      player.sendChatMessage('Hello 👋 Pokémon!');
      
      expect(mockWebSocket.send).toHaveBeenCalledWith('test-room|Hello 👋 Pokémon!');
    });

    it('should truncate overly long messages', () => {
      const longMessage = 'A'.repeat(1000);
      player.sendChatMessage(longMessage);
      
      // Should truncate to max length (300 chars for PS)
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        expect.stringContaining('test-room|' + 'A'.repeat(300))
      );
    });
  });

  describe('Chat History', () => {
    it('should maintain chat history', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      
      // Receive multiple messages
      messageHandler(Buffer.from('>test-room\n|c|User1|First message'));
      messageHandler(Buffer.from('>test-room\n|c|User2|Second message'));
      messageHandler(Buffer.from('>test-room\n|c|User1|Third message'));
      
      const history = player.getChatHistory('test-room');
      
      expect(history).toHaveLength(3);
      expect(history[0].message).toBe('First message');
      expect(history[2].message).toBe('Third message');
    });

    it('should limit chat history size', () => {
      const messageHandler = mockWebSocket.on.mock.calls.find(call => call[0] === 'message')[1];
      
      // Send 150 messages
      for (let i = 0; i < 150; i++) {
        messageHandler(Buffer.from(`>test-room\n|c|User|Message ${i}`));
      }
      
      const history = player.getChatHistory('test-room');
      
      // Should keep only last 100 messages
      expect(history).toHaveLength(100);
      expect(history[0].message).toBe('Message 50');
      expect(history[99].message).toBe('Message 149');
    });
  });
});