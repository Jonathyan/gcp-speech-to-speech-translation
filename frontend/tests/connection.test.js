describe('WebSocket Audio Streaming', () => {
  let mockWebSocket;
  
  beforeEach(() => {
    // Mock WebSocket
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      readyState: 1, // OPEN
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null
    };
    
    global.WebSocket = jest.fn(() => mockWebSocket);
    global.WebSocket.OPEN = 1;
    global.WebSocket.CONNECTING = 0;
    
    // Mock window dependencies
    global.window = {
      AppConfig: {
        CONFIG: {
          CONNECTION: {
            maxRetries: 3,
            retryDelayBase: 1000
          }
        }
      },
      AppUI: {
        updateStatus: jest.fn(),
        enableButtons: jest.fn()
      }
    };
    
    // Reset rate limiting
    jest.clearAllTimers();
    jest.useFakeTimers();
    
    // Clear module cache to reset internal state
    jest.resetModules();
  });
  
  afterEach(() => {
    delete global.WebSocket;
    delete global.window;
    jest.useRealTimers();
  });

  test('sendAudioChunk sends binary data via WebSocket', () => {
    const connection = require('../src/connection.js');
    
    const audioData = new ArrayBuffer(1000);
    const result = connection.sendAudioChunk(mockWebSocket, audioData);
    
    expect(mockWebSocket.send).toHaveBeenCalledWith(audioData);
    expect(result.success).toBe(true);
  });

  test('sendAudioChunk handles WebSocket not ready', () => {
    const connection = require('../src/connection.js');
    
    mockWebSocket.readyState = 0; // CONNECTING
    const audioData = new ArrayBuffer(1000);
    const result = connection.sendAudioChunk(mockWebSocket, audioData);
    
    expect(mockWebSocket.send).not.toHaveBeenCalled();
    expect(result.success).toBe(false);
    expect(result.error).toBe('WebSocket not ready');
  });

  test('sendAudioChunk handles send errors gracefully', () => {
    const connection = require('../src/connection.js');
    
    // Create a separate mock WebSocket for this test
    const errorWebSocket = {
      ...mockWebSocket,
      send: jest.fn(() => {
        throw new Error('Network error');
      })
    };
    
    const audioData = new ArrayBuffer(1000);
    const result = connection.sendAudioChunk(errorWebSocket, audioData);
    
    expect(result.success).toBe(false);
    expect(result.error).toBe('Failed to send audio chunk');
  });

  test('sendAudioChunk implements rate limiting', () => {
    const connection = require('../src/connection.js');
    
    const audioData = new ArrayBuffer(1000);
    
    // Send chunks to exceed rate limit (MAX_SENDS_PER_WINDOW = 10)
    const results = [];
    for (let i = 0; i < 12; i++) {
      results.push(connection.sendAudioChunk(mockWebSocket, audioData));
    }
    
    // First 10 should succeed
    for (let i = 0; i < 10; i++) {
      expect(results[i].success).toBe(true);
    }
    
    // 11th and 12th should be rate limited
    expect(results[10].success).toBe(false);
    expect(results[10].error).toBe('Rate limited');
    expect(results[11].success).toBe(false);
    expect(results[11].error).toBe('Rate limited');
  });

  test('connectWebSocket uses correct endpoint for broadcast mode', () => {
    const connection = require('../src/connection.js');
    
    connection.connectWebSocket('ws://localhost:8000', 'broadcast', 'test-stream');
    
    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws/speak/test-stream');
  });

  test('connectWebSocket uses correct endpoint for listener mode', () => {
    const connection = require('../src/connection.js');
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws/listen/test-stream');
  });

  test('connectWebSocket generates stream_id when not provided', () => {
    const connection = require('../src/connection.js');
    
    connection.connectWebSocket('ws://localhost:8000', 'broadcast');
    
    const callArgs = global.WebSocket.mock.calls[0][0];
    expect(callArgs).toMatch(/ws:\/\/localhost:8000\/ws\/speak\/stream-\d+/);
  });

  test('connectWebSocket handles connection errors during streaming', () => {
    const connection = require('../src/connection.js');
    
    connection.connectWebSocket('ws://localhost:8000', 'broadcast', 'test-stream');
    
    // Simulate connection error
    const errorHandler = mockWebSocket.onerror;
    expect(errorHandler).toBeDefined();
    
    const mockError = new Error('Connection lost');
    errorHandler(mockError);
    
    // Should handle error gracefully without crashing
    expect(true).toBe(true); // Test passes if no exception thrown
  });

  test('connectWebSocket sets up binary message handling', () => {
    const connection = require('../src/connection.js');
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    expect(mockWebSocket.onmessage).toBeDefined();
    
    // Simulate binary message
    const binaryData = new ArrayBuffer(500);
    const mockEvent = { data: binaryData };
    
    mockWebSocket.onmessage(mockEvent);
    
    // Should handle binary data without errors
    expect(true).toBe(true);
  });
});

describe('AudioPlayer Integration', () => {
  let mockWebSocket;
  let mockAudioPlayer;
  let connection;
  
  beforeEach(() => {
    // Mock WebSocket
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      readyState: 1,
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null
    };
    
    global.WebSocket = jest.fn(() => mockWebSocket);
    global.WebSocket.OPEN = 1;
    
    // Mock AudioPlayer
    mockAudioPlayer = {
      createAudioContext: jest.fn(),
      decodeAudioChunk: jest.fn(),
      validateAudioBuffer: jest.fn(),
      addToQueue: jest.fn(),
      startStreamPlayback: jest.fn(),
      stopStreamPlayback: jest.fn(),
      clearQueue: jest.fn(),
      getQueueSize: jest.fn(),
      isStreaming: false
    };
    
    global.AudioPlayer = jest.fn(() => mockAudioPlayer);
    
    // Mock window dependencies
    global.window = {
      AppConfig: {
        CONFIG: {
          CONNECTION: {
            maxRetries: 3,
            retryDelayBase: 1000
          }
        }
      },
      AppUI: {
        updateStatus: jest.fn(),
        enableButtons: jest.fn()
      }
    };
    
    connection = require('../src/connection.js');
  });
  
  afterEach(() => {
    delete global.WebSocket;
    delete global.AudioPlayer;
    delete global.window;
  });

  test('initializeAudioPlayer creates AudioPlayer instance', () => {
    connection.initializeAudioPlayer();
    
    expect(global.AudioPlayer).toHaveBeenCalled();
    expect(mockAudioPlayer.createAudioContext).toHaveBeenCalled();
  });

  test('initializeAudioPlayer handles AudioPlayer not available', () => {
    delete global.AudioPlayer;
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    connection.initializeAudioPlayer();
    
    expect(consoleSpy).toHaveBeenCalledWith('AudioPlayer class not available');
    consoleSpy.mockRestore();
  });

  test('initializeAudioPlayer handles creation errors', () => {
    global.AudioPlayer = jest.fn(() => {
      throw new Error('AudioContext creation failed');
    });
    
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    connection.initializeAudioPlayer();
    
    expect(consoleSpy).toHaveBeenCalledWith('Failed to initialize AudioPlayer:', expect.any(Error));
    consoleSpy.mockRestore();
  });

  test('connectWebSocket initializes AudioPlayer for listener mode', () => {
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    expect(global.AudioPlayer).toHaveBeenCalled();
    expect(mockAudioPlayer.createAudioContext).toHaveBeenCalled();
  });

  test('connectWebSocket does not initialize AudioPlayer for broadcast mode', () => {
    connection.connectWebSocket('ws://localhost:8000', 'broadcast', 'test-stream');
    
    expect(global.AudioPlayer).not.toHaveBeenCalled();
  });

  test('handleIncomingAudioData processes audio with AudioPlayer', async () => {
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    mockAudioPlayer.decodeAudioChunk.mockResolvedValue(mockAudioBuffer);
    mockAudioPlayer.validateAudioBuffer.mockReturnValue({ valid: true, errors: [] });
    mockAudioPlayer.addToQueue.mockReturnValue(true);
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const audioData = new ArrayBuffer(1000);
    const mockEvent = { data: audioData };
    
    // Simulate receiving audio data
    mockWebSocket.onmessage(mockEvent);
    
    // Wait for async processing
    await new Promise(resolve => setTimeout(resolve, 10));
    
    expect(mockAudioPlayer.decodeAudioChunk).toHaveBeenCalledWith(audioData);
    expect(mockAudioPlayer.validateAudioBuffer).toHaveBeenCalledWith(mockAudioBuffer);
    expect(mockAudioPlayer.addToQueue).toHaveBeenCalledWith(mockAudioBuffer);
  });

  test('handleIncomingAudioData handles decoding errors', async () => {
    mockAudioPlayer.decodeAudioChunk.mockRejectedValue(new Error('Decode failed'));
    
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const audioData = new ArrayBuffer(1000);
    const mockEvent = { data: audioData };
    
    mockWebSocket.onmessage(mockEvent);
    
    await new Promise(resolve => setTimeout(resolve, 10));
    
    expect(consoleSpy).toHaveBeenCalledWith('Audio processing error:', expect.any(Error));
    consoleSpy.mockRestore();
  });

  test('handleIncomingAudioData handles validation errors', async () => {
    const mockAudioBuffer = { duration: 0, sampleRate: 0, numberOfChannels: 0 };
    mockAudioPlayer.decodeAudioChunk.mockResolvedValue(mockAudioBuffer);
    mockAudioPlayer.validateAudioBuffer.mockReturnValue({ 
      valid: false, 
      errors: ['Invalid duration', 'Invalid sample rate'] 
    });
    
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const audioData = new ArrayBuffer(1000);
    const mockEvent = { data: audioData };
    
    mockWebSocket.onmessage(mockEvent);
    
    await new Promise(resolve => setTimeout(resolve, 10));
    
    expect(consoleSpy).toHaveBeenCalledWith('Invalid audio buffer:', ['Invalid duration', 'Invalid sample rate']);
    expect(mockAudioPlayer.addToQueue).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  test('handleIncomingMessage processes JSON control messages', () => {
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const controlMessage = JSON.stringify({ type: 'audio_start' });
    const mockEvent = { data: controlMessage };
    
    mockWebSocket.onmessage(mockEvent);
    
    expect(mockAudioPlayer.startStreamPlayback).toHaveBeenCalled();
  });

  test('handleIncomingMessage handles audio_end message', () => {
    mockAudioPlayer.isStreaming = true;
    mockAudioPlayer.getQueueSize.mockReturnValue(0);
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const controlMessage = JSON.stringify({ type: 'audio_end' });
    const mockEvent = { data: controlMessage };
    
    jest.useFakeTimers();
    mockWebSocket.onmessage(mockEvent);
    
    jest.advanceTimersByTime(1000);
    
    expect(mockAudioPlayer.stopStreamPlayback).toHaveBeenCalled();
    jest.useRealTimers();
  });

  test('handleIncomingMessage handles plain text messages', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const textMessage = 'Plain text message';
    const mockEvent = { data: textMessage };
    
    mockWebSocket.onmessage(mockEvent);
    
    expect(consoleSpy).toHaveBeenCalledWith('Text message received:', textMessage);
    consoleSpy.mockRestore();
  });

  test('cleanupAudioPlayer stops playback and clears queue', () => {
    connection.initializeAudioPlayer();
    connection.cleanupAudioPlayer();
    
    expect(mockAudioPlayer.stopStreamPlayback).toHaveBeenCalled();
    expect(mockAudioPlayer.clearQueue).toHaveBeenCalled();
  });

  test('disconnectWebSocket cleans up AudioPlayer', () => {
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    connection.disconnectWebSocket();
    
    expect(mockAudioPlayer.stopStreamPlayback).toHaveBeenCalled();
    expect(mockAudioPlayer.clearQueue).toHaveBeenCalled();
  });

  test('getAudioStats returns audio processing statistics', () => {
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const stats = connection.getAudioStats();
    
    expect(stats).toHaveProperty('chunksReceived');
    expect(stats).toHaveProperty('bytesReceived');
    expect(stats).toHaveProperty('chunksProcessed');
    expect(stats).toHaveProperty('processingErrors');
  });

  test('audio statistics are updated correctly', async () => {
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    mockAudioPlayer.decodeAudioChunk.mockResolvedValue(mockAudioBuffer);
    mockAudioPlayer.validateAudioBuffer.mockReturnValue({ valid: true, errors: [] });
    mockAudioPlayer.addToQueue.mockReturnValue(true);
    
    connection.connectWebSocket('ws://localhost:8000', 'listener', 'test-stream');
    
    const audioData = new ArrayBuffer(1000);
    const mockEvent = { data: audioData };
    
    mockWebSocket.onmessage(mockEvent);
    
    await new Promise(resolve => setTimeout(resolve, 10));
    
    const stats = connection.getAudioStats();
    expect(stats.chunksReceived).toBe(1);
    expect(stats.bytesReceived).toBe(1000);
    expect(stats.chunksProcessed).toBe(1);
    expect(stats.processingErrors).toBe(0);
  });
});