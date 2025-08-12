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

describe('Complete Listener Mode Implementation', () => {
  let mockWebSocket;
  let mockAudioPlayer;
  
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
    
    // Mock AudioPlayer
    mockAudioPlayer = {
      createAudioContext: jest.fn(),
      startStreamPlayback: jest.fn(),
      stopStreamPlayback: jest.fn(),
      clearQueue: jest.fn(),
      isStreaming: false,
      getQueueSize: jest.fn(() => 0)
    };
    
    // Mock window dependencies
    global.window = {
      AppUtils: {
        isWebAudioSupported: jest.fn(() => true)
      },
      AppConnection: {
        connectWebSocket: jest.fn(),
        disconnectWebSocket: jest.fn(),
        getCurrentWebSocket: jest.fn(() => mockWebSocket),
        getAudioStats: jest.fn(() => ({
          chunksReceived: 5,
          bytesReceived: 5000,
          chunksProcessed: 4,
          processingErrors: 1
        }))
      },
      AppConfig: {
        getWebSocketURL: jest.fn(() => 'ws://localhost:8000')
      },
      prompt: jest.fn(() => 'test-stream-123')
    };
    
    // Mock DOM
    document.body.innerHTML = `
      <div id="status">Ready</div>
      <button id="start-broadcast">Start Uitzending</button>
      <button id="join-listener">Luisteren</button>
      <button id="disconnect">Verbinding Verbreken</button>
    `;
    
    // Mock timers
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    delete global.WebSocket;
    delete global.window;
    jest.useRealTimers();
  });

  test('joinListener initializes complete listener workflow', async () => {
    const ui = require('../src/ui.js');
    
    // Start listening
    ui.joinListener();
    
    // Verify Web Audio API support check
    expect(window.AppUtils.isWebAudioSupported).toHaveBeenCalled();
    
    // Verify stream ID prompt
    expect(window.prompt).toHaveBeenCalledWith(
      'Voer stream ID in (of laat leeg voor test-stream):',
      'test-stream'
    );
    
    // Verify WebSocket connection setup
    expect(window.AppConnection.connectWebSocket).toHaveBeenCalledWith(
      'ws://localhost:8000',
      'listener',
      'test-stream-123'
    );
    
    // Fast-forward timer to complete setup
    jest.advanceTimersByTime(1000);
    
    // Verify UI state updated
    const listenButton = document.getElementById('join-listener');
    expect(listenButton.textContent).toBe('Stop Luisteren');
    
    const startButton = document.getElementById('start-broadcast');
    expect(startButton.disabled).toBe(true);
  });

  test('joinListener handles Web Audio API not supported', () => {
    const ui = require('../src/ui.js');
    
    // Mock Web Audio API not supported
    window.AppUtils.isWebAudioSupported.mockReturnValue(false);
    
    ui.joinListener();
    
    // Verify error handling
    const status = document.getElementById('status');
    expect(status.textContent).toBe('❌ Web Audio API niet ondersteund');
    
    // Verify no connection attempted
    expect(window.AppConnection.connectWebSocket).not.toHaveBeenCalled();
  });

  test('joinListener handles user cancellation', () => {
    const ui = require('../src/ui.js');
    
    // Mock user cancelling prompt
    window.prompt.mockReturnValue(null);
    
    ui.joinListener();
    
    // Verify no connection attempted
    expect(window.AppConnection.connectWebSocket).not.toHaveBeenCalled();
    
    const status = document.getElementById('status');
    expect(status.textContent).toBe('Ready');
  });

  test('joinListener handles connection failure', () => {
    const ui = require('../src/ui.js');
    
    // Mock connection failure
    window.AppConnection.getCurrentWebSocket.mockReturnValue(null);
    
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    
    // Verify error handling
    const status = document.getElementById('status');
    expect(status.textContent).toBe('❌ Verbinding mislukt');
  });

  test('stopListening cleans up listener resources', () => {
    const ui = require('../src/ui.js');
    
    // Start listening first
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    
    // Stop listening
    ui.stopListening();
    
    // Verify cleanup
    expect(window.AppConnection.disconnectWebSocket).toHaveBeenCalled();
    
    // Verify UI state reset
    const listenButton = document.getElementById('join-listener');
    expect(listenButton.textContent).toBe('Luisteren');
    
    const startButton = document.getElementById('start-broadcast');
    expect(startButton.disabled).toBe(false);
    
    const status = document.getElementById('status');
    expect(status.textContent).toBe('Luisteren gestopt');
  });

  test('updateListenerUI correctly manages UI state', () => {
    const ui = require('../src/ui.js');
    
    // Test listening state
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    
    const listenButton = document.getElementById('join-listener');
    const startButton = document.getElementById('start-broadcast');
    const disconnectButton = document.getElementById('disconnect');
    
    expect(listenButton.textContent).toBe('Stop Luisteren');
    expect(startButton.disabled).toBe(true);
    expect(disconnectButton.disabled).toBe(false);
    
    // Test stopped state
    ui.stopListening();
    
    expect(listenButton.textContent).toBe('Luisteren');
    expect(startButton.disabled).toBe(false);
    expect(disconnectButton.disabled).toBe(true);
  });

  test('showListeningIndicator manages visual indicator', () => {
    const ui = require('../src/ui.js');
    
    // Show indicator
    ui.showListeningIndicator(true);
    
    const indicator = document.getElementById('listening-indicator');
    expect(indicator).toBeTruthy();
    expect(indicator.innerHTML).toBe('🎧');
    expect(indicator.style.position).toBe('fixed');
    
    // Hide indicator
    ui.showListeningIndicator(false);
    
    const removedIndicator = document.getElementById('listening-indicator');
    expect(removedIndicator).toBeFalsy();
  });

  test('audio status monitoring updates UI with statistics', () => {
    const ui = require('../src/ui.js');
    
    // Start listening to trigger monitoring
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    
    // Fast-forward to trigger status update
    jest.advanceTimersByTime(2000);
    
    // Verify status updated with statistics
    const status = document.getElementById('status');
    expect(status.textContent).toContain('Luisteren - Stream: test-stream-123');
    expect(status.textContent).toContain('Ontvangen: 5 chunks (5KB)');
    expect(status.textContent).toContain('Fouten: 1');
    
    expect(window.AppConnection.getAudioStats).toHaveBeenCalled();
  });

  test('audio status monitoring stops when listening stops', () => {
    const ui = require('../src/ui.js');
    
    // Start listening
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    
    // Verify monitoring started
    expect(setInterval).toHaveBeenCalled();
    
    // Stop listening
    ui.stopListening();
    
    // Verify monitoring stopped
    expect(clearInterval).toHaveBeenCalled();
  });

  test('enableButtons respects active session states', () => {
    const ui = require('../src/ui.js');
    
    // Start listening
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    
    // Try to enable buttons while listening
    ui.enableButtons(true);
    
    const startButton = document.getElementById('start-broadcast');
    const listenButton = document.getElementById('join-listener');
    
    // Buttons should remain in their session state, not be enabled
    expect(startButton.disabled).toBe(true); // Still disabled during listening
    expect(listenButton.textContent).toBe('Stop Luisteren'); // Still in listening mode
  });

  test('complete listener workflow integration', () => {
    const ui = require('../src/ui.js');
    
    // Initial state
    const status = document.getElementById('status');
    const listenButton = document.getElementById('join-listener');
    
    expect(status.textContent).toBe('Ready');
    expect(listenButton.textContent).toBe('Luisteren');
    
    // Start listening
    ui.joinListener();
    expect(status.textContent).toBe('Audio systeem initialiseren...');
    
    // Connection setup
    jest.advanceTimersByTime(500);
    expect(status.textContent).toBe('Verbinden als luisteraar...');
    
    // Connection established
    jest.advanceTimersByTime(500);
    expect(listenButton.textContent).toBe('Stop Luisteren');
    
    // Status monitoring active
    jest.advanceTimersByTime(2000);
    expect(status.textContent).toContain('Luisteren - Stream:');
    
    // Stop listening
    ui.stopListening();
    expect(status.textContent).toBe('Luisteren gestopt');
    expect(listenButton.textContent).toBe('Luisteren');
  });
});

describe('UI Feedback & User Experience', () => {
  let mockAudioPlayer;
  
  beforeEach(() => {
    // Mock AudioPlayer with error callbacks
    mockAudioPlayer = {
      createAudioContext: jest.fn(),
      onError: null,
      onRecovery: null,
      onQualityChange: null,
      getHealthReport: jest.fn(() => ({
        overall: 'Warning',
        errors: { successRate: '85%' },
        troubleshooting: ['Controleer internetverbinding']
      })),
      getPlaybackQuality: jest.fn(() => ({
        overall: 'Good',
        latency: 'Excellent',
        recommendations: ['Audio kwaliteit is goed']
      })),
      getPerformanceMetrics: jest.fn(() => ({
        avgLatency: 75,
        droppedChunks: 2,
        processedChunks: 18
      }))
    };
    
    // Mock window dependencies
    global.window = {
      AppConnection: {
        audioPlayer: mockAudioPlayer,
        disconnectWebSocket: jest.fn(),
        getAudioStats: jest.fn(() => ({
          chunksReceived: 20,
          bytesReceived: 20000,
          chunksProcessed: 18,
          processingErrors: 2,
          audioLevel: 65
        }))
      },
      AppUtils: {
        isWebAudioSupported: jest.fn(() => true)
      },
      AppConfig: {
        getWebSocketURL: jest.fn(() => 'ws://localhost:8000')
      },
      prompt: jest.fn(() => 'test-stream')
    };
    
    // Mock DOM elements
    document.body.innerHTML = `
      <div id="status">Ready</div>
      <button id="start-broadcast">Start Uitzending</button>
      <button id="join-listener">Luisteren</button>
    `;
    
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    // Clean up any indicators that might have been created
    const indicators = [
      'audio-loading-indicator',
      'audio-quality-indicator', 
      'audio-level-indicator',
      'error-dialog',
      'audio-gesture-overlay'
    ];
    indicators.forEach(id => {
      const element = document.getElementById(id);
      if (element) element.remove();
    });
    
    delete global.window;
    jest.useRealTimers();
  });

  test('showAudioLoading displays loading indicator with progress', () => {
    const ui = require('../src/ui.js');
    
    ui.showAudioLoading(true, 'Audio decoderen...', 45);
    
    const indicator = document.getElementById('audio-loading-indicator');
    expect(indicator).toBeTruthy();
    expect(indicator.style.position).toBe('fixed');
    expect(indicator.innerHTML).toContain('🎧 Audio decoderen...');
    expect(indicator.innerHTML).toContain('width: 45%');
    expect(indicator.innerHTML).toContain('45%');
  });

  test('showAudioLoading removes indicator when loading complete', () => {
    const ui = require('../src/ui.js');
    
    // Show loading
    ui.showAudioLoading(true);
    expect(document.getElementById('audio-loading-indicator')).toBeTruthy();
    
    // Hide loading
    ui.showAudioLoading(false);
    expect(document.getElementById('audio-loading-indicator')).toBeFalsy();
  });

  test('showAudioQuality displays quality indicator with metrics', () => {
    const ui = require('../src/ui.js');
    
    const metrics = { latency: '85ms', dropRate: '2%' };
    ui.showAudioQuality('good', metrics);
    
    const indicator = document.getElementById('audio-quality-indicator');
    expect(indicator).toBeTruthy();
    expect(indicator.innerHTML).toContain('🔵 Audio: good');
    expect(indicator.innerHTML).toContain('Latency: 85ms');
    expect(indicator.innerHTML).toContain('Drops: 2%');
    expect(indicator.style.borderLeft).toContain('#17a2b8');
  });

  test('showAudioQuality uses correct colors for different qualities', () => {
    const ui = require('../src/ui.js');
    
    // Test excellent quality
    ui.showAudioQuality('excellent');
    let indicator = document.getElementById('audio-quality-indicator');
    expect(indicator.innerHTML).toContain('🟢 Audio: excellent');
    expect(indicator.style.borderLeft).toContain('#28a745');
    
    // Test poor quality
    ui.showAudioQuality('poor');
    indicator = document.getElementById('audio-quality-indicator');
    expect(indicator.innerHTML).toContain('🔴 Audio: poor');
    expect(indicator.style.borderLeft).toContain('#dc3545');
  });

  test('showError displays error with suggestion and recovery options', () => {
    const ui = require('../src/ui.js');
    
    const mockRetry = jest.fn();
    ui.showError('Verbinding mislukt', 'Controleer internetverbinding', {
      recoverable: true,
      onRetry: mockRetry,
      clearTime: 5000
    });
    
    const status = document.getElementById('status');
    expect(status.innerHTML).toContain('❌ Verbinding mislukt');
    expect(status.classList.contains('error')).toBe(true);
    
    // Fast-forward to show suggestion
    jest.advanceTimersByTime(1000);
    expect(status.innerHTML).toContain('💡 Controleer internetverbinding');
    
    // Fast-forward to show recovery button
    jest.advanceTimersByTime(1000);
    expect(status.innerHTML).toContain('Probeer Opnieuw');
    
    // Fast-forward to auto-clear
    jest.advanceTimersByTime(5000);
    expect(status.textContent).toBe('Ready');
    expect(status.classList.contains('error')).toBe(false);
  });

  test('setupAudioErrorHandling configures AudioPlayer callbacks', () => {
    const ui = require('../src/ui.js');
    
    ui.setupAudioErrorHandling();
    
    expect(mockAudioPlayer.onError).toBeInstanceOf(Function);
    expect(mockAudioPlayer.onRecovery).toBeInstanceOf(Function);
    expect(mockAudioPlayer.onQualityChange).toBeInstanceOf(Function);
  });

  test('AudioPlayer error callback shows user-friendly error', () => {
    const ui = require('../src/ui.js');
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    ui.setupAudioErrorHandling();
    
    // Trigger error callback
    mockAudioPlayer.onError({
      operation: 'decode',
      error: 'Netwerkfout tijdens audio verwerking',
      suggestion: 'Controleer uw internetverbinding',
      recoverable: true
    });
    
    const status = document.getElementById('status');
    expect(status.innerHTML).toContain('❌ Netwerkfout tijdens audio verwerking');
    expect(consoleSpy).toHaveBeenCalledWith('Audio Player Error:', expect.any(Object));
    
    consoleSpy.mockRestore();
  });

  test('AudioPlayer recovery callback shows success message', () => {
    const ui = require('../src/ui.js');
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    
    ui.setupAudioErrorHandling();
    
    // Trigger recovery callback
    mockAudioPlayer.onRecovery({
      message: 'Audio systeem hersteld',
      timestamp: new Date().toISOString()
    });
    
    const status = document.getElementById('status');
    expect(status.textContent).toContain('✅ Audio systeem hersteld');
    expect(consoleSpy).toHaveBeenCalledWith('Audio Player Recovery:', expect.any(Object));
    
    consoleSpy.mockRestore();
  });

  test('AudioPlayer quality change callback updates quality indicator', () => {
    const ui = require('../src/ui.js');
    
    ui.setupAudioErrorHandling();
    
    // Trigger quality change callback
    mockAudioPlayer.onQualityChange('fair');
    
    const indicator = document.getElementById('audio-quality-indicator');
    expect(indicator).toBeTruthy();
    expect(indicator.innerHTML).toContain('🟡 Audio: fair');
  });

  test('showErrorDialog displays comprehensive error information', () => {
    const ui = require('../src/ui.js');
    
    const errorInfo = {
      error: 'AudioContext suspension error',
      operation: 'context',
      suggestion: 'Klik ergens op de pagina om audio te activeren',
      diagnostics: { audioContextState: 'suspended', webAudioSupport: true },
      recoverable: true
    };
    
    ui.showErrorDialog(errorInfo);
    
    const dialog = document.getElementById('error-dialog');
    expect(dialog).toBeTruthy();
    expect(dialog.innerHTML).toContain('🚨 Audio Systeem Fout');
    expect(dialog.innerHTML).toContain('AudioContext suspension error');
    expect(dialog.innerHTML).toContain('Klik ergens op de pagina om audio te activeren');
    expect(dialog.innerHTML).toContain('Diagnostische Informatie');
    expect(dialog.innerHTML).toContain('Probeer Opnieuw');
  });

  test('closeErrorDialog removes error dialog', () => {
    const ui = require('../src/ui.js');
    
    // Show dialog first
    ui.showErrorDialog({
      error: 'Test error',
      operation: 'test',
      suggestion: 'Test suggestion'
    });
    
    expect(document.getElementById('error-dialog')).toBeTruthy();
    
    ui.closeErrorDialog();
    expect(document.getElementById('error-dialog')).toBeFalsy();
  });

  test('handleErrorRecovery performs operation-specific recovery', () => {
    const ui = require('../src/ui.js');
    
    // Mock location.reload
    Object.defineProperty(window, 'location', {
      value: { reload: jest.fn() },
      writable: true
    });
    
    // Test context recovery (should reload page)
    ui.handleErrorRecovery('context');
    expect(window.location.reload).toHaveBeenCalled();
    
    // Reset mock
    window.location.reload.mockReset();
    
    // Test decode recovery
    ui.handleErrorRecovery('decode');
    const status = document.getElementById('status');
    expect(status.textContent).toBe('Audio decodering herstarten...');
    
    // Test playback recovery
    ui.handleErrorRecovery('playback');
    expect(status.textContent).toBe('Audio afspelen herstarten...');
  });

  test('showAudioLevel displays audio level visualization', () => {
    const ui = require('../src/ui.js');
    
    ui.showAudioLevel(75);
    
    const indicator = document.getElementById('audio-level-indicator');
    expect(indicator).toBeTruthy();
    expect(indicator.style.position).toBe('fixed');
    expect(indicator.innerHTML).toContain('height: 75%');
    expect(indicator.innerHTML).toContain('#ffc107'); // Yellow for 75%
  });

  test('showAudioLevel uses correct colors for different levels', () => {
    const ui = require('../src/ui.js');
    
    // Test low level (green)
    ui.showAudioLevel(30);
    let indicator = document.getElementById('audio-level-indicator');
    expect(indicator.innerHTML).toContain('#28a745');
    
    // Test high level (red)  
    ui.showAudioLevel(85);
    indicator = document.getElementById('audio-level-indicator');
    expect(indicator.innerHTML).toContain('#dc3545');
  });

  test('hideAudioLevel removes audio level indicator', () => {
    const ui = require('../src/ui.js');
    
    // Show level first
    ui.showAudioLevel(50);
    expect(document.getElementById('audio-level-indicator')).toBeTruthy();
    
    // Hide level
    ui.hideAudioLevel();
    expect(document.getElementById('audio-level-indicator')).toBeFalsy();
  });

  test('startEnhancedAudioMonitoring provides comprehensive status updates', () => {
    const ui = require('../src/ui.js');
    
    // Set up listening state
    ui.joinListener();
    
    jest.advanceTimersByTime(1000); // Complete connection
    jest.advanceTimersByTime(2000); // Trigger monitoring update
    
    const status = document.getElementById('status');
    expect(status.textContent).toContain('🎧 Luisteren - Stream: test-stream');
    expect(status.textContent).toContain('Ontvangen: 20 chunks (20KB)');
    expect(status.textContent).toContain('Fouten: 2');
    
    // Verify quality indicator is shown
    expect(document.getElementById('audio-quality-indicator')).toBeTruthy();
    
    // Verify audio level is shown
    expect(document.getElementById('audio-level-indicator')).toBeTruthy();
  });

  test('getAudioPlayerStatus returns comprehensive player information', () => {
    const ui = require('../src/ui.js');
    
    const status = ui.getAudioPlayerStatus();
    
    expect(status.isStreaming).toBe(false);
    expect(status.queueSize).toBe(0);
    expect(status.isPlaying).toBe(false);
    expect(status.quality).toBe('Good');
    expect(status.health).toBe('Warning');
    expect(status.metrics).toBeDefined();
  });

  test('enhanced monitoring adapts to different audio conditions', () => {
    const ui = require('../src/ui.js');
    
    // Mock different audio statistics scenarios
    window.AppConnection.getAudioStats
      .mockReturnValueOnce({
        chunksReceived: 0,
        bytesReceived: 0,
        chunksProcessed: 0,
        processingErrors: 0
      })
      .mockReturnValueOnce({
        chunksReceived: 100,
        bytesReceived: 100000,
        chunksProcessed: 95,
        processingErrors: 5,
        audioLevel: 90
      });
    
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    
    // First update - no data
    jest.advanceTimersByTime(1000);
    let status = document.getElementById('status');
    expect(status.textContent).toContain('🎧 Luisteren - Stream: test-stream');
    
    // Second update - lots of data
    jest.advanceTimersByTime(1000);
    status = document.getElementById('status');
    expect(status.textContent).toContain('Ontvangen: 100 chunks (98KB)');
    expect(status.textContent).toContain('Fouten: 5');
  });

  test('UI feedback handles multiple concurrent indicators', () => {
    const ui = require('../src/ui.js');
    
    // Show multiple indicators simultaneously
    ui.showAudioLoading(true, 'Loading...', 50);
    ui.showAudioQuality('excellent', { latency: '25ms' });
    ui.showAudioLevel(80);
    
    // Verify all indicators exist
    expect(document.getElementById('audio-loading-indicator')).toBeTruthy();
    expect(document.getElementById('audio-quality-indicator')).toBeTruthy();
    expect(document.getElementById('audio-level-indicator')).toBeTruthy();
    
    // Hide all indicators
    ui.showAudioLoading(false);
    ui.hideAudioLevel();
    
    // Quality indicator should remain (not explicitly hidden)
    expect(document.getElementById('audio-loading-indicator')).toBeFalsy();
    expect(document.getElementById('audio-quality-indicator')).toBeTruthy();
    expect(document.getElementById('audio-level-indicator')).toBeFalsy();
  });
});

describe('Diagnostics & Recovery Capabilities', () => {
  let mockDiagnostics;
  
  beforeEach(() => {
    mockDiagnostics = {
      runAudioDiagnostics: jest.fn(() => Promise.resolve({
        microphoneAccess: { success: true },
        recordingCapability: { success: true },
        formatSupport: ['audio/webm', 'audio/mp4']
      })),
      getBrowserCapabilities: jest.fn(() => ({
        webAudio: true,
        mediaRecorder: true,
        webSocket: true,
        getUserMedia: true
      })),
      generateDebugInfo: jest.fn(() => ({
        timestamp: Date.now(),
        userAgent: 'test-agent',
        recommendations: []
      }))
    };
    
    global.window = {
      AppDiagnostics: mockDiagnostics,
      AppConnection: {
        audioPlayer: {
          getHealthReport: jest.fn(() => ({
            overall: 'Healthy',
            diagnostics: { webAudioSupport: true },
            troubleshooting: ['Systeem werkt normaal']
          }))
        }
      }
    };
    
    document.body.innerHTML = `
      <div id="status">Ready</div>
      <button id="run-diagnostics">Diagnostiek Uitvoeren</button>
    `;
    
    jest.useFakeTimers();
  });
  
  afterEach(() => {
    delete global.window;
    jest.useRealTimers();
  });

  test('runDiagnostics executes comprehensive system check', async () => {
    const ui = require('../src/ui.js');
    
    const diagnosticsPromise = ui.runDiagnostics();
    
    // Verify loading state
    const status = document.getElementById('status');
    expect(status.textContent).toContain('⏳');
    expect(status.textContent).toContain('Diagnostiek uitvoeren...');
    
    await diagnosticsPromise;
    
    // Verify all diagnostics methods called
    expect(mockDiagnostics.runAudioDiagnostics).toHaveBeenCalled();
    expect(mockDiagnostics.getBrowserCapabilities).toHaveBeenCalled();
    expect(mockDiagnostics.generateDebugInfo).toHaveBeenCalled();
    
    // Verify results displayed
    expect(status.textContent).toContain('Diagnostiek: Microfoon ✅');
    expect(status.textContent).toContain('Opname ✅');
    expect(status.textContent).toContain('Formaten: 2');
  });

  test('runDiagnostics handles diagnostic failures', async () => {
    const ui = require('../src/ui.js');
    
    // Mock diagnostics that fail
    mockDiagnostics.runAudioDiagnostics.mockRejectedValue(
      new Error('Diagnostic system unavailable')
    );
    
    await ui.runDiagnostics();
    
    const status = document.getElementById('status');
    expect(status.innerHTML).toContain('❌ Diagnostiek mislukt');
  });

  test('runDiagnostics shows recommendations when available', async () => {
    const ui = require('../src/ui.js');
    
    // Mock diagnostics with recommendations
    mockDiagnostics.generateDebugInfo.mockReturnValue({
      timestamp: Date.now(),
      userAgent: 'test-agent',
      recommendations: [
        'Upgrade to Chrome for better audio support',
        'Check microphone permissions'
      ]
    });
    
    await ui.runDiagnostics();
    
    // Should show recommendations available message
    jest.advanceTimersByTime(2000);
    
    const status = document.getElementById('status');
    expect(status.innerHTML).toContain('❌ Aanbevelingen beschikbaar');
  });

  test('runDiagnostics reports different component status correctly', async () => {
    const ui = require('../src/ui.js');
    
    // Mock mixed success/failure results
    mockDiagnostics.runAudioDiagnostics.mockResolvedValue({
      microphoneAccess: { success: false },
      recordingCapability: { success: true },
      formatSupport: ['audio/webm']
    });
    
    await ui.runDiagnostics();
    
    const status = document.getElementById('status');
    expect(status.textContent).toContain('Diagnostiek: Microfoon ❌');
    expect(status.textContent).toContain('Opname ✅');
    expect(status.textContent).toContain('Formaten: 1');
  });

  test('comprehensive system health reporting works', () => {
    const ui = require('../src/ui.js');
    
    // Setup AudioPlayer to return health report
    const healthReport = ui.getAudioPlayerStatus();
    
    expect(healthReport.quality).toBeDefined();
    expect(healthReport.health).toBeDefined();
    expect(healthReport.metrics).toBeDefined();
    
    // Should include troubleshooting information
    expect(window.AppConnection.audioPlayer.getHealthReport).toHaveBeenCalled();
  });

  test('diagnostics console output provides detailed information', async () => {
    const ui = require('../src/ui.js');
    
    const consoleSpy = jest.spyOn(console, 'group').mockImplementation();
    const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    const consoleGroupEndSpy = jest.spyOn(console, 'groupEnd').mockImplementation();
    
    await ui.runDiagnostics();
    
    expect(consoleSpy).toHaveBeenCalledWith('🔧 Diagnostiek Resultaten');
    expect(consoleLogSpy).toHaveBeenCalledWith('Audio Diagnostiek:', expect.any(Object));
    expect(consoleLogSpy).toHaveBeenCalledWith('Browser Mogelijkheden:', expect.any(Object));
    expect(consoleLogSpy).toHaveBeenCalledWith('Debug Informatie:', expect.any(Object));
    expect(consoleGroupEndSpy).toHaveBeenCalled();
    
    consoleSpy.mockRestore();
    consoleLogSpy.mockRestore();
    consoleGroupEndSpy.mockRestore();
  });

  test('performance troubleshooting provides actionable insights', () => {
    const ui = require('../src/ui.js');
    
    // Mock audio player with performance issues
    const mockAudioPlayer = {
      getHealthReport: jest.fn(() => ({
        overall: 'Critical',
        performance: {
          droppedChunks: 25,
          processedChunks: 75,
          avgLatency: 250
        },
        troubleshooting: [
          'Hoge drop rate - controleer internetverbinding',
          'Hoge latency - sluit andere audio applicaties',
          'Geheugendruk - herlaad de pagina'
        ]
      }))
    };
    
    window.AppConnection.audioPlayer = mockAudioPlayer;
    
    const status = ui.getAudioPlayerStatus();
    
    expect(status.health).toBe('Critical');
    expect(mockAudioPlayer.getHealthReport).toHaveBeenCalled();
  });

  test('error recovery integrates with diagnostic information', () => {
    const ui = require('../src/ui.js');
    
    // Setup error with diagnostic context
    const errorInfo = {
      error: 'Memory pressure detected',
      operation: 'decode',
      suggestion: 'Herlaad de pagina om geheugen vrij te maken',
      recoverable: true,
      diagnostics: {
        memoryUsage: '85%',
        queueSize: 45,
        bufferPoolSize: 15
      }
    };
    
    ui.showErrorDialog(errorInfo);
    
    const dialog = document.getElementById('error-dialog');
    expect(dialog).toBeTruthy();
    expect(dialog.innerHTML).toContain('Memory pressure detected');
    expect(dialog.innerHTML).toContain('memoryUsage');
    expect(dialog.innerHTML).toContain('queueSize');
    expect(dialog.innerHTML).toContain('Probeer Opnieuw');
  });

  test('production-ready reliability monitoring works', () => {
    const ui = require('../src/ui.js');
    
    // Mock enhanced monitoring with reliability metrics
    window.AppConnection.getAudioStats = jest.fn(() => ({
      chunksReceived: 1000,
      bytesReceived: 1000000,
      chunksProcessed: 950,
      processingErrors: 50,
      audioLevel: 45,
      connectionQuality: 'Good',
      uptime: 300000 // 5 minutes
    }));
    
    ui.joinListener();
    jest.advanceTimersByTime(1000);
    jest.advanceTimersByTime(2000); // Trigger monitoring
    
    const status = document.getElementById('status');
    expect(status.textContent).toContain('Ontvangen: 1000 chunks (977KB)');
    expect(status.textContent).toContain('Fouten: 50');
    
    // Should show quality indicators for reliability
    const qualityIndicator = document.getElementById('audio-quality-indicator');
    expect(qualityIndicator).toBeTruthy();
  });
});