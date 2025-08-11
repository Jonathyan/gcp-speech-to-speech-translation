describe('E2E Integration Tests', () => {
  beforeEach(() => {
    // Load actual HTML and JS files
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(path.join(__dirname, '../public/index.html'), 'utf8');
    document.documentElement.innerHTML = html;
    
    // Clear any existing modules
    jest.resetModules();
    require('../src/app.js');
    
    // Trigger DOMContentLoaded
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);
  });

  describe('Complete User Flow', () => {
    test('Load page and verify initial state', () => {
      // Verify page loads correctly
      expect(document.title).toBe('Live Speech Translation');
      expect(document.getElementById('start-broadcast')).toBeTruthy();
      expect(document.getElementById('join-listener')).toBeTruthy();
      expect(document.getElementById('status').textContent).toBe('Ready');
    });

    test('Click Start Uitzending triggers connection attempt', async () => {
      const startButton = document.getElementById('start-broadcast');
      const status = document.getElementById('status');
      
      // Mock WebSocket to simulate connection attempt
      const mockWs = {
        close: jest.fn(),
        addEventListener: jest.fn(),
        readyState: 0 // CONNECTING
      };
      global.WebSocket = jest.fn(() => mockWs);
      
      // Click button
      startButton.click();
      
      // Verify connection attempt
      expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws');
      expect(status.textContent).toBe('Verbinden...');
    });

    test('Status updates during connection lifecycle', () => {
      const status = document.getElementById('status');
      
      // Test status progression
      global.updateStatus('Verbinden...');
      expect(status.textContent).toBe('Verbinden...');
      
      global.updateStatus('Verbonden - Klaar om uit te zenden');
      expect(status.textContent).toBe('Verbonden - Klaar om uit te zenden');
      
      global.updateStatus('Verbinding gesloten');
      expect(status.textContent).toBe('Verbinding gesloten');
    });
  });

  describe('Error Scenarios', () => {
    test('WebSocket not supported', () => {
      // Simulate browser without WebSocket support
      const originalWebSocket = global.WebSocket;
      global.WebSocket = undefined;
      
      expect(() => {
        global.connectWebSocket('ws://localhost:8000/ws', 'broadcast');
      }).not.toThrow();
      
      // Restore
      global.WebSocket = originalWebSocket;
    });

    test('Server not available', async () => {
      const status = document.getElementById('status');
      
      // Mock WebSocket that fails immediately
      global.WebSocket = jest.fn(() => {
        const mockWs = {
          close: jest.fn(),
          addEventListener: jest.fn()
        };
        // Simulate immediate error
        setTimeout(() => {
          if (mockWs.onerror) mockWs.onerror();
        }, 0);
        return mockWs;
      });
      
      global.connectWebSocket('ws://localhost:8000/ws', 'broadcast');
      
      // Wait for async error handling
      await new Promise(resolve => setTimeout(resolve, 10));
      
      expect(status.textContent).toContain('Verbinding mislukt');
    });

    test('Connection retry logic', async () => {
      const status = document.getElementById('status');
      let callCount = 0;
      
      // Mock WebSocket that fails first few times
      global.WebSocket = jest.fn(() => {
        callCount++;
        const mockWs = {
          close: jest.fn(),
          addEventListener: jest.fn()
        };
        
        if (callCount <= 2) {
          setTimeout(() => {
            if (mockWs.onerror) mockWs.onerror();
          }, 0);
        }
        
        return mockWs;
      });
      
      global.connectWebSocket('ws://localhost:8000/ws', 'broadcast');
      
      // Verify retry attempts
      expect(global.WebSocket).toHaveBeenCalled();
    });
  });

  describe('UI Responsiveness', () => {
    test('Buttons state management', () => {
      const startButton = document.getElementById('start-broadcast');
      const listenButton = document.getElementById('join-listener');
      const disconnectButton = document.getElementById('disconnect');
      
      // Initial state
      expect(startButton.disabled).toBe(false);
      expect(listenButton.disabled).toBe(false);
      expect(disconnectButton.disabled).toBe(true);
      
      // During connection
      global.enableButtons(false);
      expect(startButton.disabled).toBe(true);
      expect(listenButton.disabled).toBe(true);
      expect(disconnectButton.disabled).toBe(false);
      
      // After disconnect
      global.enableButtons(true);
      expect(startButton.disabled).toBe(false);
      expect(listenButton.disabled).toBe(false);
      expect(disconnectButton.disabled).toBe(true);
    });

    test('No JavaScript errors during normal flow', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      // Simulate normal user flow
      global.startBroadcast();
      global.updateStatus('Test status');
      global.disconnectWebSocket();
      
      expect(consoleSpy).not.toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });
});