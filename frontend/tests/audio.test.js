describe('Audio Microphone Access', () => {
  beforeEach(() => {
    // Reset global mocks
    delete global.navigator;
    jest.clearAllMocks();
  });

  test('requestMicrophoneAccess succeeds with getUserMedia', async () => {
    const audio = require('../src/audio.js');
    
    // Mock successful getUserMedia
    const mockStream = { getTracks: jest.fn(() => [{ stop: jest.fn() }]) };
    global.navigator = {
      mediaDevices: {
        getUserMedia: jest.fn().mockResolvedValue(mockStream)
      }
    };
    
    const result = await audio.requestMicrophoneAccess();
    
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(result.success).toBe(true);
    expect(result.stream).toBe(mockStream);
    expect(result.error).toBeUndefined();
  });

  test('requestMicrophoneAccess handles permission denied', async () => {
    const audio = require('../src/audio.js');
    
    // Mock permission denied
    const permissionError = new Error('Permission denied');
    permissionError.name = 'NotAllowedError';
    global.navigator = {
      mediaDevices: {
        getUserMedia: jest.fn().mockRejectedValue(permissionError)
      }
    };
    
    const result = await audio.requestMicrophoneAccess();
    
    expect(result.success).toBe(false);
    expect(result.stream).toBeNull();
    expect(result.error).toBe('Permission denied');
  });

  test('requestMicrophoneAccess handles browser not supported', async () => {
    const audio = require('../src/audio.js');
    
    // No navigator.mediaDevices
    global.navigator = {};
    
    const result = await audio.requestMicrophoneAccess();
    
    expect(result.success).toBe(false);
    expect(result.stream).toBeNull();
    expect(result.error).toBe('Microphone access not supported');
  });

  test('stopAudioStream stops all tracks', () => {
    const audio = require('../src/audio.js');
    
    const mockTrack1 = { stop: jest.fn() };
    const mockTrack2 = { stop: jest.fn() };
    const mockStream = {
      getTracks: jest.fn(() => [mockTrack1, mockTrack2])
    };
    
    audio.stopAudioStream(mockStream);
    
    expect(mockStream.getTracks).toHaveBeenCalled();
    expect(mockTrack1.stop).toHaveBeenCalled();
    expect(mockTrack2.stop).toHaveBeenCalled();
  });

  test('stopAudioStream handles null stream gracefully', () => {
    const audio = require('../src/audio.js');
    
    // Should not throw error
    expect(() => audio.stopAudioStream(null)).not.toThrow();
    expect(() => audio.stopAudioStream(undefined)).not.toThrow();
  });
});

describe('AudioRecorder Class', () => {
  let mockStream;
  let mockMediaRecorder;
  
  beforeEach(() => {
    // Mock MediaStream
    mockStream = {
      getTracks: jest.fn(() => [{ stop: jest.fn() }])
    };
    
    // Mock MediaRecorder
    mockMediaRecorder = {
      start: jest.fn(),
      stop: jest.fn(),
      addEventListener: jest.fn(),
      state: 'inactive',
      ondataavailable: null,
      onerror: null
    };
    
    global.MediaRecorder = jest.fn(() => mockMediaRecorder);
    global.MediaRecorder.isTypeSupported = jest.fn(() => true);
  });
  
  afterEach(() => {
    delete global.MediaRecorder;
  });

  test('AudioRecorder instantiation with default options', () => {
    const audio = require('../src/audio.js');
    
    const recorder = new audio.AudioRecorder(mockStream);
    
    expect(global.MediaRecorder).toHaveBeenCalledWith(mockStream, {
      mimeType: 'audio/webm',
      timeslice: 250
    });
    expect(recorder.stream).toBe(mockStream);
    expect(recorder.isRecording).toBe(false);
  });

  test('AudioRecorder with custom options', () => {
    const audio = require('../src/audio.js');
    
    const options = {
      mimeType: 'audio/mp4',
      timeslice: 500,
      onDataAvailable: jest.fn()
    };
    
    const recorder = new audio.AudioRecorder(mockStream, options);
    
    expect(global.MediaRecorder).toHaveBeenCalledWith(mockStream, {
      mimeType: 'audio/mp4',
      timeslice: 500
    });
    expect(recorder.onDataCallback).toBe(options.onDataAvailable);
  });

  test('AudioRecorder start method', () => {
    const audio = require('../src/audio.js');
    const onDataCallback = jest.fn();
    
    const recorder = new audio.AudioRecorder(mockStream, { onDataAvailable: onDataCallback });
    recorder.start();
    
    expect(mockMediaRecorder.start).toHaveBeenCalledWith(250);
    expect(recorder.isRecording).toBe(true);
  });

  test('AudioRecorder stop method', () => {
    const audio = require('../src/audio.js');
    
    const recorder = new audio.AudioRecorder(mockStream);
    recorder.start();
    recorder.stop();
    
    expect(mockMediaRecorder.stop).toHaveBeenCalled();
    expect(recorder.isRecording).toBe(false);
  });

  test('AudioRecorder data callback setup', () => {
    const audio = require('../src/audio.js');
    const onDataCallback = jest.fn();
    
    const recorder = new audio.AudioRecorder(mockStream, { onDataAvailable: onDataCallback });
    
    // Simulate data available event
    const mockEvent = { data: new Blob(['test'], { type: 'audio/webm' }) };
    recorder.mediaRecorder.ondataavailable(mockEvent);
    
    expect(onDataCallback).toHaveBeenCalledWith(mockEvent.data);
  });

  test('AudioRecorder handles MediaRecorder errors', () => {
    const audio = require('../src/audio.js');
    const onErrorCallback = jest.fn();
    
    const recorder = new audio.AudioRecorder(mockStream, { onError: onErrorCallback });
    
    // Simulate error event
    const mockError = new Error('Recording failed');
    recorder.mediaRecorder.onerror(mockError);
    
    expect(onErrorCallback).toHaveBeenCalledWith(mockError);
    expect(recorder.isRecording).toBe(false);
  });

  test('AudioRecorder format fallback', () => {
    const audio = require('../src/audio.js');
    
    // Mock webm not supported, mp4 supported
    global.MediaRecorder.isTypeSupported = jest.fn((type) => type === 'audio/mp4');
    
    const recorder = new audio.AudioRecorder(mockStream);
    
    expect(global.MediaRecorder).toHaveBeenCalledWith(mockStream, {
      mimeType: 'audio/mp4',
      timeslice: 250
    });
  });

  test('AudioRecorder throws error when no supported format', () => {
    const audio = require('../src/audio.js');
    
    // Mock no formats supported
    global.MediaRecorder.isTypeSupported = jest.fn(() => false);
    
    expect(() => {
      new audio.AudioRecorder(mockStream);
    }).toThrow('No supported audio format found');
  });
});

describe('Audio Format Conversion & Validation', () => {
  beforeEach(() => {
    // Mock FileReader
    global.FileReader = jest.fn(() => ({
      readAsArrayBuffer: jest.fn(),
      onload: null,
      onerror: null,
      result: new ArrayBuffer(1000)
    }));
  });
  
  afterEach(() => {
    delete global.FileReader;
  });

  test('convertAudioChunk converts Blob to ArrayBuffer', async () => {
    const audio = require('../src/audio.js');
    
    // Mock FileReader with proper async behavior
    const mockResult = new ArrayBuffer(1000);
    global.FileReader = jest.fn(() => ({
      readAsArrayBuffer: jest.fn(function() {
        // Simulate async completion
        setTimeout(() => {
          this.result = mockResult;
          if (this.onload) this.onload();
        }, 0);
      }),
      onload: null,
      onerror: null,
      result: null
    }));
    
    const mockBlob = new Blob(['test audio data'], { type: 'audio/webm' });
    const result = await audio.convertAudioChunk(mockBlob);
    
    expect(result).toBeInstanceOf(ArrayBuffer);
    expect(result.byteLength).toBe(1000);
  });

  test('convertAudioChunk handles empty blob', async () => {
    const audio = require('../src/audio.js');
    
    const emptyBlob = new Blob([], { type: 'audio/webm' });
    
    await expect(audio.convertAudioChunk(emptyBlob)).rejects.toThrow('Audio data is empty');
  });

  test('convertAudioChunk handles conversion errors', async () => {
    const audio = require('../src/audio.js');
    
    // Mock FileReader error
    global.FileReader = jest.fn(() => ({
      readAsArrayBuffer: jest.fn(),
      onload: null,
      onerror: null
    }));
    
    const mockBlob = new Blob(['test'], { type: 'audio/webm' });
    
    // Simulate error by triggering onerror
    const conversionPromise = audio.convertAudioChunk(mockBlob);
    const reader = global.FileReader.mock.results[0].value;
    setTimeout(() => {
      if (reader.onerror) reader.onerror(new Error('Read failed'));
    }, 0);
    
    await expect(conversionPromise).rejects.toThrow('Failed to convert audio chunk');
  });

  test('validateAudioChunk accepts valid size', () => {
    const audio = require('../src/audio.js');
    
    const validBuffer = new ArrayBuffer(5000); // 5KB
    const result = audio.validateAudioChunk(validBuffer);
    
    expect(result.isValid).toBe(true);
    expect(result.size).toBe(5000);
  });

  test('validateAudioChunk rejects too small chunks', () => {
    const audio = require('../src/audio.js');
    
    const tooSmall = new ArrayBuffer(50); // 50 bytes
    const result = audio.validateAudioChunk(tooSmall);
    
    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Audio chunk too small (50 bytes)');
  });

  test('validateAudioChunk rejects too large chunks', () => {
    const audio = require('../src/audio.js');
    
    const tooLarge = new ArrayBuffer(200 * 1024); // 200KB
    const result = audio.validateAudioChunk(tooLarge);
    
    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Audio chunk too large (204800 bytes)');
  });

  test('validateAudioChunk handles null input', () => {
    const audio = require('../src/audio.js');
    
    const result = audio.validateAudioChunk(null);
    
    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Invalid audio data');
  });
});