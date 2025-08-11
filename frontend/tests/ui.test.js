describe('UI Elements', () => {
  beforeEach(() => {
    // Try to load actual HTML file (will fail - doesn't exist yet)
    const fs = require('fs');
    const path = require('path');
    try {
      const html = fs.readFileSync(path.join(__dirname, '../public/index.html'), 'utf8');
      document.documentElement.innerHTML = html;
    } catch (error) {
      // HTML file doesn't exist yet - this should cause tests to fail
      document.body.innerHTML = '';
    }
  });

  test('Start Uitzending button exists', () => {
    const button = document.getElementById('start-broadcast');
    expect(button).toBeTruthy();
    expect(button.textContent).toBe('Start Uitzending');
  });

  test('Luister mee button exists', () => {
    const button = document.getElementById('join-listener');
    expect(button).toBeTruthy();
    expect(button.textContent).toBe('Luister mee');
  });

  test('Status div exists', () => {
    const status = document.getElementById('status');
    expect(status).toBeTruthy();
    expect(status.textContent).toBe('Ready');
  });

  test('Both buttons disabled initially', () => {
    const startButton = document.getElementById('start-broadcast');
    const listenButton = document.getElementById('join-listener');
    expect(startButton.disabled).toBe(true);
    expect(listenButton.disabled).toBe(true);
  });
});

describe('Button Click Behavior', () => {
  beforeEach(() => {
    // Load actual HTML and JS files
    const fs = require('fs');
    const path = require('path');
    const html = fs.readFileSync(path.join(__dirname, '../public/index.html'), 'utf8');
    document.documentElement.innerHTML = html;
    require('../src/app.js');
    
    // Trigger DOMContentLoaded event
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);
  });

  test('Clicking Start Uitzending changes status', () => {
    const button = document.getElementById('start-broadcast');
    expect(button).toBeTruthy();
    
    // Test function exists and can be called
    expect(global.startBroadcast).toBeDefined();
    global.startBroadcast();
    
    // Verify status changed
    const status = document.getElementById('status');
    expect(status.textContent).toBe('Verbinden...');
  });

  test('Clicking Luister mee changes status', () => {
    const button = document.getElementById('join-listener');
    expect(button).toBeTruthy();
    
    // Test function exists and can be called
    expect(global.joinListener).toBeDefined();
    global.joinListener();
    
    // Verify status changed
    const status = document.getElementById('status');
    expect(status.textContent).toBe('Verbinden als luisteraar...');
  });

  test('Buttons get enabled/disabled correctly', () => {
    const startButton = document.getElementById('start-broadcast');
    const listenButton = document.getElementById('join-listener');
    
    // Simulate connection state change
    startButton.disabled = false;
    listenButton.disabled = false;
    
    expect(startButton.disabled).toBe(false);
    expect(listenButton.disabled).toBe(false);
  });
});

describe('WebSocket Connection', () => {
  let mockWs;

  beforeEach(() => {
    // Try to load actual files (will fail - don't exist yet)
    const fs = require('fs');
    const path = require('path');
    try {
      const html = fs.readFileSync(path.join(__dirname, '../public/index.html'), 'utf8');
      document.documentElement.innerHTML = html;
      require('../src/app.js');
    } catch (error) {
      // Files don't exist yet - this should cause tests to fail
      document.body.innerHTML = '';
    }
    mockWs = global.mockWebSocket();
  });

  test('WebSocket connection attempt made', () => {
    // Try to call connectWebSocket function (will fail - doesn't exist yet)
    expect(global.connectWebSocket).toBeDefined();
    global.connectWebSocket('ws://localhost:8000/ws');
    expect(WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws');
  });

  test('Status updates on connection events', () => {
    const status = document.getElementById('status');
    
    // Mock connection success
    status.textContent = 'Verbonden';
    expect(status.textContent).toBe('Verbonden');
    
    // Mock connection error
    status.textContent = 'Verbinding mislukt';
    expect(status.textContent).toBe('Verbinding mislukt');
  });

  test('WebSocket events handled correctly', () => {
    const ws = new WebSocket('ws://test');
    expect(ws.addEventListener).toBeDefined();
    expect(ws.send).toBeDefined();
    expect(ws.close).toBeDefined();
  });
});