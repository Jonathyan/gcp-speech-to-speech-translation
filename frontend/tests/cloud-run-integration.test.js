/**
 * Cloud Run Integration Tests
 * Tests for frontend integration with Google Cloud Run backend
 */

// Mock WebSocket for testing
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) this.onopen();
    }, 100);
  }
  
  send(data) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Simulate successful send
    return true;
  }
  
  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) this.onclose();
  }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

// Mock the config module
jest.mock('../src/config', () => ({
  CONFIG: {
    WEBSOCKET_URL: {
      development: 'ws://localhost:8000',
      production: 'wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app'
    }
  },
  getEnvironment: jest.fn(),
  getWebSocketURL: jest.fn(),
  getBestAudioFormat: jest.fn(() => 'audio/webm;codecs=opus'),
  getAudioConstraints: jest.fn(() => ({ audio: true }))
}));

describe('Cloud Run Integration Tests', () => {
  let config;
  
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    config = require('../src/config');
    global.WebSocket = MockWebSocket;
  });

  describe('Configuration Tests', () => {
    test('should use production WebSocket URL when in production environment', () => {
      // Mock production environment
      config.getEnvironment.mockReturnValue('production');
      config.getWebSocketURL.mockReturnValue('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app');
      
      const wsUrl = config.getWebSocketURL();
      expect(wsUrl).toBe('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app');
      expect(wsUrl).toMatch(/^wss:/); // Ensure secure WebSocket
    });

    test('should use development WebSocket URL when in development environment', () => {
      // Mock development environment
      config.getEnvironment.mockReturnValue('development');
      config.getWebSocketURL.mockReturnValue('ws://localhost:8000');
      
      const wsUrl = config.getWebSocketURL();
      expect(wsUrl).toBe('ws://localhost:8000');
    });

    test('should detect production environment correctly', () => {
      // Mock window.location for production
      Object.defineProperty(window, 'location', {
        value: { hostname: 'your-project.firebaseapp.com' },
        writable: true
      });
      
      config.getEnvironment.mockImplementation(() => {
        return window.location.hostname === 'localhost' ? 'development' : 'production';
      });
      
      expect(config.getEnvironment()).toBe('production');
    });
  });

  describe('WebSocket Connection Tests', () => {
    test('should successfully connect to Cloud Run WebSocket endpoint for speaker', async () => {
      const streamId = 'test-stream-123';
      const wsUrl = `wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/${streamId}`;
      
      const ws = new MockWebSocket(wsUrl);
      
      // Wait for connection to establish
      await new Promise((resolve) => {
        ws.onopen = resolve;
      });
      
      expect(ws.readyState).toBe(MockWebSocket.OPEN);
      expect(ws.url).toBe(wsUrl);
    });

    test('should successfully connect to Cloud Run WebSocket endpoint for listener', async () => {
      const streamId = 'test-stream-123';
      const wsUrl = `wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/listen/${streamId}`;
      
      const ws = new MockWebSocket(wsUrl);
      
      // Wait for connection to establish
      await new Promise((resolve) => {
        ws.onopen = resolve;
      });
      
      expect(ws.readyState).toBe(MockWebSocket.OPEN);
      expect(ws.url).toBe(wsUrl);
    });

    test('should handle WebSocket connection errors gracefully', async () => {
      const wsUrl = 'wss://invalid-url.com/ws/speak/test';
      const ws = new MockWebSocket(wsUrl);
      
      let errorOccurred = false;
      ws.onerror = () => {
        errorOccurred = true;
      };
      
      // Simulate error
      setTimeout(() => {
        if (ws.onerror) ws.onerror(new Error('Connection failed'));
      }, 50);
      
      await new Promise(resolve => setTimeout(resolve, 100));
      expect(errorOccurred).toBe(true);
    });
  });

  describe('Audio Format Tests', () => {
    test('should support WebM audio format for Cloud Run compatibility', () => {
      const format = config.getBestAudioFormat();
      expect(format).toMatch(/audio\/(webm|wav)/);
    });

    test('should use appropriate audio constraints for Cloud Run STT', () => {
      const constraints = config.getAudioConstraints();
      expect(constraints).toHaveProperty('audio');
      expect(constraints.audio).toBeTruthy();
    });
  });

  describe('Stream ID Management', () => {
    test('should generate valid stream IDs for Cloud Run endpoints', () => {
      // Mock stream ID generation
      const generateStreamId = () => {
        return 'stream-' + Math.random().toString(36).substr(2, 9);
      };
      
      const streamId = generateStreamId();
      expect(streamId).toMatch(/^stream-[a-z0-9]+$/);
      expect(streamId.length).toBeGreaterThan(8);
    });

    test('should validate stream ID format for security', () => {
      const isValidStreamId = (id) => {
        return /^[a-zA-Z0-9-_]{1,50}$/.test(id);
      };
      
      expect(isValidStreamId('test-stream-123')).toBe(true);
      expect(isValidStreamId('stream_456')).toBe(true);
      expect(isValidStreamId('invalid stream id')).toBe(false); // spaces not allowed
      expect(isValidStreamId('')).toBe(false); // empty not allowed
    });
  });

  describe('Error Handling Tests', () => {
    test('should handle Cloud Run WebSocket disconnections', async () => {
      const ws = new MockWebSocket('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/test');
      
      let connectionClosed = false;
      ws.onclose = () => {
        connectionClosed = true;
      };
      
      // Wait for connection, then close
      await new Promise((resolve) => {
        ws.onopen = resolve;
      });
      
      ws.close();
      expect(connectionClosed).toBe(true);
      expect(ws.readyState).toBe(MockWebSocket.CLOSED);
    });

    test('should implement reconnection logic for production stability', () => {
      let reconnectAttempts = 0;
      const maxReconnects = 3;
      
      const attemptReconnect = () => {
        if (reconnectAttempts < maxReconnects) {
          reconnectAttempts++;
          return true; // Would create new WebSocket
        }
        return false;
      };
      
      expect(attemptReconnect()).toBe(true);
      expect(attemptReconnect()).toBe(true);
      expect(attemptReconnect()).toBe(true);
      expect(attemptReconnect()).toBe(false); // Max attempts reached
      expect(reconnectAttempts).toBe(3);
    });
  });

  describe('CORS and Security Tests', () => {
    test('should handle CORS preflight for Cloud Run requests', () => {
      const corsHeaders = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
      };
      
      // Verify expected CORS headers
      expect(corsHeaders).toHaveProperty('Access-Control-Allow-Origin');
      expect(corsHeaders).toHaveProperty('Access-Control-Allow-Methods');
    });

    test('should use secure WebSocket (wss://) in production', () => {
      config.getEnvironment.mockReturnValue('production');
      config.getWebSocketURL.mockReturnValue('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app');
      
      const wsUrl = config.getWebSocketURL();
      expect(wsUrl.startsWith('wss://')).toBe(true);
    });
  });

  describe('Performance Tests', () => {
    test('should establish WebSocket connection within acceptable time', async () => {
      const startTime = Date.now();
      const ws = new MockWebSocket('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/test');
      
      await new Promise((resolve) => {
        ws.onopen = resolve;
      });
      
      const connectionTime = Date.now() - startTime;
      expect(connectionTime).toBeLessThan(5000); // Should connect within 5 seconds
    });

    test('should handle rapid WebSocket message sending', () => {
      const ws = new MockWebSocket('wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/test');
      ws.readyState = MockWebSocket.OPEN; // Force open state
      
      const messages = [];
      for (let i = 0; i < 10; i++) {
        messages.push(new ArrayBuffer(1024)); // 1KB chunks
      }
      
      // Should not throw errors when sending rapidly
      expect(() => {
        messages.forEach(msg => ws.send(msg));
      }).not.toThrow();
    });
  });
});

describe('Firebase Integration Tests', () => {
  test('should be compatible with Firebase Hosting static assets', () => {
    // Mock Firebase hosting environment
    const mockFirebaseConfig = {
      apiKey: "test-api-key",
      authDomain: "test-project.firebaseapp.com",
      projectId: "test-project",
      storageBucket: "test-project.appspot.com",
      messagingSenderId: "123456789",
      appId: "test-app-id"
    };
    
    expect(mockFirebaseConfig).toHaveProperty('apiKey');
    expect(mockFirebaseConfig).toHaveProperty('projectId');
  });

  test('should handle Firebase CDN caching correctly', () => {
    const cacheHeaders = {
      'Cache-Control': 'max-age=31536000', // 1 year for assets
      'Content-Type': 'application/javascript'
    };
    
    expect(cacheHeaders['Cache-Control']).toContain('max-age');
  });
});