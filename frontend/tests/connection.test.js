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