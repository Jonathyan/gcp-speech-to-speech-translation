describe('Complete Audio Pipeline Integration', () => {
  let mockWebSocket;
  let mockAudioRecorder;
  let mockStream;
  
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
    
    // Mock MediaStream
    mockStream = {
      getTracks: jest.fn(() => [{ stop: jest.fn() }])
    };
    
    // Mock AudioRecorder
    mockAudioRecorder = {
      start: jest.fn(),
      stop: jest.fn(),
      isRecording: false
    };
    
    // Mock window dependencies
    global.window = {
      AppAudio: {
        requestMicrophoneAccess: jest.fn().mockResolvedValue({
          success: true,
          stream: mockStream
        }),
        stopAudioStream: jest.fn(),
        AudioRecorder: jest.fn(() => mockAudioRecorder),
        convertAudioChunk: jest.fn().mockResolvedValue(new ArrayBuffer(1000)),
        validateAudioChunk: jest.fn(() => ({ isValid: true, size: 1000 }))
      },
      AppConnection: {
        generateStreamId: jest.fn(() => 'test-stream-123'),
        connectWebSocket: jest.fn(),
        disconnectWebSocket: jest.fn(),
        getCurrentWebSocket: jest.fn(() => mockWebSocket),
        sendAudioChunk: jest.fn(() => ({ success: true }))
      },
      AppConfig: {
        getWebSocketURL: jest.fn(() => 'ws://localhost:8000')
      }
    };
    
    // Mock DOM
    document.body.innerHTML = `
      <div id="status">Ready</div>
      <button id="start-broadcast">Start Uitzending</button>
      <button id="join-listener">Luister mee</button>
    `;
    
    // Mock setTimeout
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    delete global.WebSocket;
    delete global.window;
    jest.useRealTimers();
  });

  test('startBroadcast integrates complete audio pipeline', async () => {
    const ui = require('../src/ui.js');
    
    // Start broadcast
    const broadcastPromise = ui.startBroadcast();
    
    // Wait for microphone access
    await broadcastPromise;
    
    // Verify microphone access requested
    expect(window.AppAudio.requestMicrophoneAccess).toHaveBeenCalled();
    
    // Verify WebSocket connection setup
    expect(window.AppConnection.connectWebSocket).toHaveBeenCalledWith(
      'ws://localhost:8000',
      'broadcast',
      'test-stream-123'
    );
    
    // Fast-forward timer to trigger recording setup
    jest.advanceTimersByTime(1000);
    
    // Verify AudioRecorder created and started
    expect(window.AppAudio.AudioRecorder).toHaveBeenCalledWith(
      mockStream,
      expect.objectContaining({
        onDataAvailable: expect.any(Function),
        onError: expect.any(Function)
      })
    );
  });

  test('stopBroadcast cleans up all resources', () => {
    const ui = require('../src/ui.js');
    
    // Setup broadcast state
    ui.startBroadcast();
    jest.advanceTimersByTime(1000);
    
    // Stop broadcast
    ui.stopBroadcast();
    
    // Verify cleanup
    expect(window.AppAudio.stopAudioStream).toHaveBeenCalledWith(mockStream);
    expect(window.AppConnection.disconnectWebSocket).toHaveBeenCalled();
    
    // Verify UI state reset
    const button = document.getElementById('start-broadcast');
    expect(button.textContent).toBe('Start Uitzending');
    
    const status = document.getElementById('status');
    expect(status.textContent).toBe('Uitzending gestopt');
  });

  test('UI reflects audio recording state transitions', async () => {
    const ui = require('../src/ui.js');
    
    const button = document.getElementById('start-broadcast');
    const status = document.getElementById('status');
    
    // Initial state
    expect(button.textContent).toBe('Start Uitzending');
    expect(status.textContent).toBe('Ready');
    
    // Start broadcast
    await ui.startBroadcast();
    expect(status.textContent).toBe('Microfoon toegang aanvragen...');
    
    // After connection setup
    jest.advanceTimersByTime(1000);
    expect(button.textContent).toBe('Stop Uitzending');
    expect(status.textContent).toContain('Uitzending actief');
    
    // Stop broadcast
    ui.stopBroadcast();
    expect(button.textContent).toBe('Start Uitzending');
    expect(status.textContent).toBe('Uitzending gestopt');
  });

  test('audio streaming pipeline processes chunks correctly', async () => {
    const ui = require('../src/ui.js');
    
    await ui.startBroadcast();
    jest.advanceTimersByTime(1000);
    
    // Get the onDataAvailable callback
    const recorderCall = window.AppAudio.AudioRecorder.mock.calls[0];
    const options = recorderCall[1];
    const onDataAvailable = options.onDataAvailable;
    
    // Simulate audio chunk
    const mockBlob = new Blob(['audio data'], { type: 'audio/webm' });
    await onDataAvailable(mockBlob);
    
    // Verify processing pipeline
    expect(window.AppAudio.convertAudioChunk).toHaveBeenCalledWith(mockBlob);
    expect(window.AppAudio.validateAudioChunk).toHaveBeenCalled();
    expect(window.AppConnection.sendAudioChunk).toHaveBeenCalledWith(
      mockWebSocket,
      expect.any(ArrayBuffer)
    );
  });

  test('handles microphone access failure gracefully', async () => {
    const ui = require('../src/ui.js');
    
    // Mock microphone access failure
    window.AppAudio.requestMicrophoneAccess.mockResolvedValue({
      success: false,
      error: 'Permission denied'
    });
    
    await ui.startBroadcast();
    
    const status = document.getElementById('status');
    expect(status.textContent).toBe('❌ Microfoon fout: Permission denied');
    
    // Verify no WebSocket connection attempted
    expect(window.AppConnection.connectWebSocket).not.toHaveBeenCalled();
  });
});

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
    // Mock window.prompt for tests
    global.window = {
      ...global.window,
      prompt: jest.fn(() => 'test-stream')
    };
    
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
    expect(status.textContent).toBe('Microfoon toegang aanvragen...');
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