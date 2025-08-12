describe('Production Audio Configuration', () => {
  beforeEach(() => {
    // Reset global mocks
    delete global.MediaRecorder;
    delete global.window;
  });

  test('getBestAudioFormat returns supported format', () => {
    const config = require('../src/config.js');
    
    // Mock MediaRecorder with webm support
    global.MediaRecorder = {
      isTypeSupported: jest.fn((type) => type === 'audio/webm')
    };
    
    const format = config.getBestAudioFormat();
    
    expect(format).toBe('audio/webm');
    expect(global.MediaRecorder.isTypeSupported).toHaveBeenCalledWith('audio/webm');
  });

  test('getBestAudioFormat falls back to mp4', () => {
    const config = require('../src/config.js');
    
    // Mock MediaRecorder with only mp4 support
    global.MediaRecorder = {
      isTypeSupported: jest.fn((type) => type === 'audio/mp4')
    };
    
    const format = config.getBestAudioFormat();
    
    expect(format).toBe('audio/mp4');
    expect(global.MediaRecorder.isTypeSupported).toHaveBeenCalledWith('audio/webm');
    expect(global.MediaRecorder.isTypeSupported).toHaveBeenCalledWith('audio/mp4');
  });

  test('getBestAudioFormat returns fallback when no support', () => {
    const config = require('../src/config.js');
    
    // Mock MediaRecorder with no support
    global.MediaRecorder = {
      isTypeSupported: jest.fn(() => false)
    };
    
    const format = config.getBestAudioFormat();
    
    expect(format).toBe('audio/webm'); // First in list as fallback
  });

  test('getBestAudioFormat handles missing MediaRecorder', () => {
    const config = require('../src/config.js');
    
    // No MediaRecorder available
    const format = config.getBestAudioFormat();
    
    expect(format).toBe('audio/webm'); // Fallback
  });

  test('getAudioConstraints returns production constraints', () => {
    const config = require('../src/config.js');
    
    const constraints = config.getAudioConstraints();
    
    expect(constraints).toEqual({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
  });

  test('getAudioChunkConfig returns production settings', () => {
    const config = require('../src/config.js');
    
    const chunkConfig = config.getAudioChunkConfig();
    
    expect(chunkConfig).toEqual({
      intervalMs: 250,
      maxSize: 100 * 1024
    });
  });

  test('CONFIG contains all required audio settings', () => {
    const config = require('../src/config.js');
    
    expect(config.CONFIG.AUDIO).toBeDefined();
    expect(config.CONFIG.AUDIO.CHUNK_INTERVAL_MS).toBe(250);
    expect(config.CONFIG.AUDIO.MAX_CHUNK_SIZE).toBe(100 * 1024);
    expect(config.CONFIG.AUDIO.AUDIO_CONSTRAINTS.audio.sampleRate).toBe(16000);
    expect(config.CONFIG.AUDIO.AUDIO_CONSTRAINTS.audio.channelCount).toBe(1);
    expect(config.CONFIG.AUDIO.SUPPORTED_MIME_TYPES).toEqual(['audio/webm', 'audio/mp4', 'audio/wav']);
  });
});