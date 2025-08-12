describe('Diagnostics Module', () => {
  beforeEach(() => {
    // Reset global mocks
    delete global.navigator;
    delete global.MediaRecorder;
    delete global.WebSocket;
    delete global.performance;
    delete global.AudioContext;
  });

  test('getBrowserCapabilities returns comprehensive report', () => {
    const diagnostics = require('../src/diagnostics.js');
    
    // Mock browser environment
    global.navigator = {
      userAgent: 'Test Browser',
      language: 'en-US',
      platform: 'Test Platform',
      cookieEnabled: true,
      onLine: true,
      mediaDevices: { getUserMedia: jest.fn() }
    };
    
    global.MediaRecorder = {
      isTypeSupported: jest.fn((type) => type === 'audio/webm')
    };
    
    global.WebSocket = jest.fn();
    global.AudioContext = jest.fn();
    
    global.performance = {
      timing: {
        loadEventEnd: 2000,
        navigationStart: 1000,
        domContentLoadedEventEnd: 1500
      },
      memory: {
        usedJSHeapSize: 1000000,
        totalJSHeapSize: 2000000,
        jsHeapSizeLimit: 4000000
      }
    };
    
    const capabilities = diagnostics.getBrowserCapabilities();
    
    expect(capabilities.browser.userAgent).toBe('Test Browser');
    expect(capabilities.audio.getUserMedia).toBe(true);
    expect(capabilities.audio.mediaRecorder).toBe(true);
    expect(capabilities.audio.supportedFormats).toContain('audio/webm');
    expect(capabilities.network.webSocket).toBe(true);
    expect(capabilities.performance.timing.loadTime).toBe(1000);
  });

  test('runAudioDiagnostics tests microphone access', async () => {
    const diagnostics = require('../src/diagnostics.js');
    
    // Mock successful microphone access
    const mockTrack = { stop: jest.fn(), getSettings: jest.fn(() => ({ sampleRate: 44100 })) };
    const mockStream = {
      getAudioTracks: jest.fn(() => [mockTrack]),
      getTracks: jest.fn(() => [mockTrack])
    };
    
    global.navigator = {
      mediaDevices: {
        getUserMedia: jest.fn().mockResolvedValue(mockStream)
      }
    };
    
    global.MediaRecorder = jest.fn(() => ({
      state: 'inactive',
      mimeType: 'audio/webm'
    }));
    
    const result = await diagnostics.runAudioDiagnostics();
    
    expect(result.microphoneAccess.success).toBe(true);
    expect(result.microphoneAccess.tracks).toBe(1);
    expect(result.recordingCapability.success).toBe(true);
    expect(mockTrack.stop).toHaveBeenCalled();
  });

  test('runAudioDiagnostics handles microphone access failure', async () => {
    const diagnostics = require('../src/diagnostics.js');
    
    // Mock failed microphone access
    global.navigator = {
      mediaDevices: {
        getUserMedia: jest.fn().mockRejectedValue(new Error('Permission denied'))
      }
    };
    
    const result = await diagnostics.runAudioDiagnostics();
    
    expect(result.microphoneAccess.success).toBe(false);
    expect(result.microphoneAccess.error).toBe('Error');
    expect(result.errors).toContain('Microphone access failed: Permission denied');
  });

  test('generateDebugInfo provides recommendations', () => {
    const diagnostics = require('../src/diagnostics.js');
    
    // Mock limited browser environment
    global.navigator = {
      userAgent: 'Limited Browser',
      language: 'en-US',
      platform: 'Test',
      cookieEnabled: true,
      onLine: true
      // No mediaDevices
    };
    
    // Mock performance
    global.performance = {
      timing: {
        loadEventEnd: 2000,
        navigationStart: 1000,
        domContentLoadedEventEnd: 1500
      }
    };
    
    // Mock window.AppConfig
    global.window = {
      AppConfig: {
        getEnvironment: jest.fn(() => 'development'),
        getAudioConstraints: jest.fn(() => ({ audio: true })),
        getAudioChunkConfig: jest.fn(() => ({ intervalMs: 250, maxSize: 100000 })),
        getBestAudioFormat: jest.fn(() => 'audio/webm')
      }
    };
    
    const debugInfo = diagnostics.generateDebugInfo();
    
    expect(debugInfo.capabilities.audio.getUserMedia).toBe(false);
    expect(debugInfo.recommendations).toContain('Upgrade to a modern browser that supports getUserMedia API');
    expect(debugInfo.config).toBeDefined();
    expect(debugInfo.config.environment).toBe('development');
  });

  test('PerformanceMetrics tracks audio chunks', () => {
    const diagnostics = require('../src/diagnostics.js');
    
    const metrics = new diagnostics.PerformanceMetrics();
    
    // Record some audio chunks
    metrics.recordAudioChunk(1000, true);
    metrics.recordAudioChunk(1500, true);
    metrics.recordAudioChunk(0, false);
    
    const report = metrics.getReport();
    
    expect(report.audioChunks.total).toBe(3);
    expect(report.audioChunks.successful).toBe(2);
    expect(report.audioChunks.failed).toBe(1);
    expect(report.audioChunks.averageSize).toBe(1250);
    expect(report.successRates.audioChunks).toBe('66.67%');
  });

  test('PerformanceMetrics tracks WebSocket events', () => {
    const diagnostics = require('../src/diagnostics.js');
    
    const metrics = new diagnostics.PerformanceMetrics();
    
    // Record WebSocket events
    metrics.recordWebSocketEvent('connect');
    metrics.recordWebSocketEvent('message', true);
    metrics.recordWebSocketEvent('message', false);
    metrics.recordWebSocketEvent('error');
    
    const report = metrics.getReport();
    
    expect(report.webSocket.connects).toBe(1);
    expect(report.webSocket.messagesSent).toBe(1);
    expect(report.webSocket.messagesFailed).toBe(1);
    expect(report.webSocket.errors).toBe(1);
    expect(report.successRates.webSocketMessages).toBe('50.00%');
  });
});