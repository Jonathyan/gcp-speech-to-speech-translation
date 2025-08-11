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