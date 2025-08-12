describe('AudioPlayer Class', () => {
  beforeEach(() => {
    // Reset global mocks
    delete global.AudioContext;
    delete global.webkitAudioContext;
    delete global.window;
  });

  test('AudioPlayer instantiation with supported browser', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    // Mock AudioContext support
    global.AudioContext = jest.fn();
    
    const player = new AudioPlayer();
    expect(player.isSupported).toBe(true);
    expect(player.audioContext).toBeNull();
  });

  test('AudioPlayer.isSupported detects AudioContext support', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    // Test when not supported
    expect(AudioPlayer.isSupported()).toBe(false);
    
    // Test when AudioContext is supported
    global.AudioContext = jest.fn();
    expect(AudioPlayer.isSupported()).toBe(true);
    
    // Test webkit fallback
    delete global.AudioContext;
    global.webkitAudioContext = jest.fn();
    expect(AudioPlayer.isSupported()).toBe(true);
  });

  test('createAudioContext creates AudioContext successfully', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    // Mock AudioContext
    const mockAudioContext = { state: 'running' };
    global.AudioContext = jest.fn(() => mockAudioContext);
    global.window = { AudioContext: global.AudioContext };
    
    const player = new AudioPlayer();
    const context = player.createAudioContext();
    
    expect(global.AudioContext).toHaveBeenCalled();
    expect(context).toBe(mockAudioContext);
    expect(player.audioContext).toBe(mockAudioContext);
  });

  test('createAudioContext handles webkit fallback', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    // Mock webkitAudioContext only
    const mockAudioContext = { state: 'running' };
    global.webkitAudioContext = jest.fn(() => mockAudioContext);
    global.window = { webkitAudioContext: global.webkitAudioContext };
    
    const player = new AudioPlayer();
    const context = player.createAudioContext();
    
    expect(global.webkitAudioContext).toHaveBeenCalled();
    expect(context).toBe(mockAudioContext);
  });

  test('createAudioContext handles suspended state', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    // Mock suspended AudioContext
    const mockAudioContext = { state: 'suspended' };
    global.AudioContext = jest.fn(() => mockAudioContext);
    global.window = { AudioContext: global.AudioContext };
    
    // Mock console.log to verify message
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    
    const player = new AudioPlayer();
    const context = player.createAudioContext();
    
    expect(context).toBe(mockAudioContext);
    expect(consoleSpy).toHaveBeenCalledWith('AudioContext suspended - will resume on user interaction');
    
    consoleSpy.mockRestore();
  });

  test('createAudioContext throws error when not supported', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    // No AudioContext support
    const player = new AudioPlayer();
    
    expect(() => {
      player.createAudioContext();
    }).toThrow('Web Audio API not supported');
  });

  test('createAudioContext handles creation errors', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    // Mock AudioContext that throws error
    global.AudioContext = jest.fn(() => {
      throw new Error('AudioContext creation failed');
    });
    global.window = { AudioContext: global.AudioContext };
    
    const player = new AudioPlayer();
    
    expect(() => {
      player.createAudioContext();
    }).toThrow('AudioContext creation failed: AudioContext creation failed');
  });
});

describe('Audio Decoding', () => {
  let mockAudioContext;
  let player;

  beforeEach(() => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    mockAudioContext = {
      state: 'running',
      decodeAudioData: jest.fn()
    };
    
    global.AudioContext = jest.fn(() => mockAudioContext);
    global.window = { AudioContext: global.AudioContext };
    
    player = new AudioPlayer();
    player.createAudioContext();
  });

  test('decodeAudioChunk decodes audio successfully', async () => {
    const mockAudioBuffer = { sampleRate: 44100, numberOfChannels: 2, duration: 1.0 };
    mockAudioContext.decodeAudioData.mockResolvedValue(mockAudioBuffer);
    
    const arrayBuffer = new ArrayBuffer(1024);
    const result = await player.decodeAudioChunk(arrayBuffer);
    
    expect(mockAudioContext.decodeAudioData).toHaveBeenCalledWith(arrayBuffer);
    expect(result).toBe(mockAudioBuffer);
  });

  test('decodeAudioChunk throws error when AudioContext not initialized', async () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    const uninitializedPlayer = new AudioPlayer();
    
    const arrayBuffer = new ArrayBuffer(1024);
    
    await expect(uninitializedPlayer.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow('AudioContext not initialized');
  });

  test('decodeAudioChunk throws error for invalid audio data', async () => {
    await expect(player.decodeAudioChunk(null))
      .rejects.toThrow('Invalid audio data');
    
    await expect(player.decodeAudioChunk(new ArrayBuffer(0)))
      .rejects.toThrow('Invalid audio data');
  });

  test('decodeAudioChunk retries on failure', async () => {
    const mockAudioBuffer = { sampleRate: 44100, numberOfChannels: 2, duration: 1.0 };
    mockAudioContext.decodeAudioData
      .mockRejectedValueOnce(new Error('Temporary failure'))
      .mockResolvedValueOnce(mockAudioBuffer);
    
    const arrayBuffer = new ArrayBuffer(1024);
    const result = await player.decodeAudioChunk(arrayBuffer);
    
    expect(mockAudioContext.decodeAudioData).toHaveBeenCalledTimes(2);
    expect(result).toBe(mockAudioBuffer);
  });

  test('decodeAudioChunk throws error after retry fails', async () => {
    mockAudioContext.decodeAudioData
      .mockRejectedValueOnce(new Error('First failure'))
      .mockRejectedValueOnce(new Error('Second failure'));
    
    const arrayBuffer = new ArrayBuffer(1024);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow('Audio decoding failed: Second failure');
    
    expect(mockAudioContext.decodeAudioData).toHaveBeenCalledTimes(2);
  });
});

describe('Audio Buffer Validation', () => {
  let player;

  beforeEach(() => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    player = new AudioPlayer();
  });

  test('validateAudioBuffer validates correct audio buffer', () => {
    const validBuffer = {
      sampleRate: 44100,
      numberOfChannels: 2,
      duration: 1.5
    };
    
    const result = player.validateAudioBuffer(validBuffer);
    
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  test('validateAudioBuffer detects null/undefined buffer', () => {
    const result1 = player.validateAudioBuffer(null);
    const result2 = player.validateAudioBuffer(undefined);
    
    expect(result1.valid).toBe(false);
    expect(result1.errors).toContain('AudioBuffer is null or undefined');
    expect(result2.valid).toBe(false);
    expect(result2.errors).toContain('AudioBuffer is null or undefined');
  });

  test('validateAudioBuffer detects invalid sample rate', () => {
    const invalidBuffer = {
      sampleRate: 0,
      numberOfChannels: 2,
      duration: 1.0
    };
    
    const result = player.validateAudioBuffer(invalidBuffer);
    
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Invalid sample rate');
  });

  test('validateAudioBuffer detects invalid channels', () => {
    const invalidBuffer = {
      sampleRate: 44100,
      numberOfChannels: 0,
      duration: 1.0
    };
    
    const result = player.validateAudioBuffer(invalidBuffer);
    
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Invalid number of channels');
  });

  test('validateAudioBuffer detects invalid duration', () => {
    const invalidBuffer = {
      sampleRate: 44100,
      numberOfChannels: 2,
      duration: 0
    };
    
    const result = player.validateAudioBuffer(invalidBuffer);
    
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('Invalid duration');
  });

  test('validateAudioBuffer detects multiple errors', () => {
    const invalidBuffer = {
      sampleRate: -1,
      numberOfChannels: 0,
      duration: -0.5
    };
    
    const result = player.validateAudioBuffer(invalidBuffer);
    
    expect(result.valid).toBe(false);
    expect(result.errors).toHaveLength(3);
    expect(result.errors).toContain('Invalid sample rate');
    expect(result.errors).toContain('Invalid number of channels');
    expect(result.errors).toContain('Invalid duration');
  });
});

describe('Audio Queue Management', () => {
  let player;
  let mockAudioBuffer1, mockAudioBuffer2, mockAudioBuffer3;

  beforeEach(() => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    player = new AudioPlayer();
    
    mockAudioBuffer1 = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    mockAudioBuffer2 = { duration: 1.5, sampleRate: 44100, numberOfChannels: 2 };
    mockAudioBuffer3 = { duration: 0.5, sampleRate: 44100, numberOfChannels: 2 };
  });

  test('addToQueue adds audio buffer successfully', () => {
    const result = player.addToQueue(mockAudioBuffer1);
    
    expect(result).toBe(true);
    expect(player.getQueueSize()).toBe(1);
  });

  test('addToQueue rejects null buffer', () => {
    const result = player.addToQueue(null);
    
    expect(result).toBe(false);
    expect(player.getQueueSize()).toBe(0);
  });

  test('getNextFromQueue returns and removes buffer', () => {
    player.addToQueue(mockAudioBuffer1);
    player.addToQueue(mockAudioBuffer2);
    
    const buffer = player.getNextFromQueue();
    
    expect(buffer).toBe(mockAudioBuffer1);
    expect(player.getQueueSize()).toBe(1);
  });

  test('getNextFromQueue returns null when empty', () => {
    const buffer = player.getNextFromQueue();
    
    expect(buffer).toBeNull();
    expect(player.getQueueSize()).toBe(0);
  });

  test('clearQueue removes all buffers', () => {
    player.addToQueue(mockAudioBuffer1);
    player.addToQueue(mockAudioBuffer2);
    player.addToQueue(mockAudioBuffer3);
    
    player.clearQueue();
    
    expect(player.getQueueSize()).toBe(0);
    expect(player.getNextFromQueue()).toBeNull();
  });

  test('getQueueSize returns correct count', () => {
    expect(player.getQueueSize()).toBe(0);
    
    player.addToQueue(mockAudioBuffer1);
    expect(player.getQueueSize()).toBe(1);
    
    player.addToQueue(mockAudioBuffer2);
    expect(player.getQueueSize()).toBe(2);
    
    player.getNextFromQueue();
    expect(player.getQueueSize()).toBe(1);
  });

  test('getQueueDuration calculates total duration', () => {
    expect(player.getQueueDuration()).toBe(0);
    
    player.addToQueue(mockAudioBuffer1); // 1.0s
    expect(player.getQueueDuration()).toBe(1.0);
    
    player.addToQueue(mockAudioBuffer2); // 1.5s
    expect(player.getQueueDuration()).toBe(2.5);
    
    player.addToQueue(mockAudioBuffer3); // 0.5s
    expect(player.getQueueDuration()).toBe(3.0);
  });

  test('queue respects maximum size limit', () => {
    // Set small max size for testing
    player.maxQueueSize = 2;
    
    player.addToQueue(mockAudioBuffer1);
    player.addToQueue(mockAudioBuffer2);
    expect(player.getQueueSize()).toBe(2);
    
    // Adding third should remove first
    player.addToQueue(mockAudioBuffer3);
    expect(player.getQueueSize()).toBe(2);
    
    // First buffer should be removed, second should be first
    const buffer = player.getNextFromQueue();
    expect(buffer).toBe(mockAudioBuffer2);
  });

  test('queue handles edge cases', () => {
    // Test with empty queue
    expect(player.getQueueDuration()).toBe(0);
    expect(player.getNextFromQueue()).toBeNull();
    
    // Test multiple clears
    player.clearQueue();
    player.clearQueue();
    expect(player.getQueueSize()).toBe(0);
    
    // Test adding after clear
    player.addToQueue(mockAudioBuffer1);
    expect(player.getQueueSize()).toBe(1);
  });

  test('queue maintains FIFO order', () => {
    player.addToQueue(mockAudioBuffer1);
    player.addToQueue(mockAudioBuffer2);
    player.addToQueue(mockAudioBuffer3);
    
    expect(player.getNextFromQueue()).toBe(mockAudioBuffer1);
    expect(player.getNextFromQueue()).toBe(mockAudioBuffer2);
    expect(player.getNextFromQueue()).toBe(mockAudioBuffer3);
    expect(player.getNextFromQueue()).toBeNull();
  });
});

describe('Audio Performance Optimization', () => {
  let player;
  let mockAudioContext;
  let mockAudioBuffer;

  beforeEach(() => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    mockAudioContext = {
      state: 'running',
      currentTime: 0,
      destination: {},
      decodeAudioData: jest.fn()
    };
    
    mockAudioBuffer = {
      duration: 1.0,
      sampleRate: 44100,
      numberOfChannels: 2
    };
    
    global.AudioContext = jest.fn(() => mockAudioContext);
    global.window = { AudioContext: global.AudioContext };
    global.performance = {
      now: jest.fn(() => Date.now()),
      memory: {
        usedJSHeapSize: 10 * 1024 * 1024,
        totalJSHeapSize: 50 * 1024 * 1024,
        jsHeapSizeLimit: 100 * 1024 * 1024
      }
    };
    
    player = new AudioPlayer();
    player.createAudioContext();
  });

  test('performance metrics are initialized correctly', () => {
    expect(player.performanceMetrics).toBeDefined();
    expect(player.performanceMetrics.processedChunks).toBe(0);
    expect(player.performanceMetrics.droppedChunks).toBe(0);
    expect(player.bufferPool).toEqual([]);
    expect(player.maxPoolSize).toBe(20);
  });

  test('decodeAudioChunk records performance metrics', async () => {
    mockAudioContext.decodeAudioData.mockResolvedValue(mockAudioBuffer);
    
    const arrayBuffer = new ArrayBuffer(1000);
    await player.decodeAudioChunk(arrayBuffer);
    
    expect(player.performanceMetrics.processedChunks).toBe(1);
    expect(player.performanceMetrics.decodeTime.length).toBe(1);
    expect(player.performanceMetrics.decodeTime[0]).toBeGreaterThanOrEqual(0);
  });

  test('decodeAudioChunk handles memory pressure', async () => {
    // Mock high memory usage
    global.performance.memory.usedJSHeapSize = 85 * 1024 * 1024; // 85% usage
    
    // Fill queue to trigger memory pressure
    for (let i = 0; i < player.maxQueueSize; i++) {
      player.addToQueue(mockAudioBuffer);
    }
    
    const arrayBuffer = new ArrayBuffer(1000);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow('Memory pressure - dropping chunk');
    
    expect(player.performanceMetrics.droppedChunks).toBe(1);
  });

  test('decodeAudioChunk handles timeout', async () => {
    // Mock slow decode that exceeds timeout
    mockAudioContext.decodeAudioData.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve(mockAudioBuffer), 200))
    );
    
    const arrayBuffer = new ArrayBuffer(1000);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow('Audio decoding timeout');
    
    expect(player.performanceMetrics.droppedChunks).toBe(1);
  });

  test('addToQueue manages memory efficiently', () => {
    const largeMockBuffer = {
      duration: 10.0,
      sampleRate: 44100,
      numberOfChannels: 2
    };
    
    // Fill queue with large buffers
    for (let i = 0; i < 10; i++) {
      player.addToQueue(largeMockBuffer);
    }
    
    expect(player.audioQueue.length).toBeLessThanOrEqual(player.maxQueueSize);
    expect(player.performanceMetrics.queueSize.length).toBeGreaterThan(0);
  });

  test('buffer pool management works correctly', () => {
    // Add buffers to queue
    for (let i = 0; i < 5; i++) {
      player.addToQueue(mockAudioBuffer);
    }
    
    // Clear queue (should return buffers to pool)
    player.clearQueue();
    
    expect(player.bufferPool.length).toBe(5);
    expect(player.audioQueue.length).toBe(0);
  });

  test('_isMemoryPressure detects high memory usage', () => {
    // Test with performance.memory available
    global.performance.memory.usedJSHeapSize = 85 * 1024 * 1024; // 85% usage
    expect(player._isMemoryPressure()).toBe(true);
    
    global.performance.memory.usedJSHeapSize = 50 * 1024 * 1024; // 50% usage
    expect(player._isMemoryPressure()).toBe(false);
  });

  test('_isMemoryPressure fallback works without performance.memory', () => {
    delete global.performance.memory;
    
    // Fill queue to trigger fallback detection
    for (let i = 0; i < player.maxQueueSize; i++) {
      player.addToQueue(mockAudioBuffer);
    }
    
    expect(player._isMemoryPressure()).toBe(true);
  });

  test('_estimateBufferMemory calculates correctly', () => {
    const memory = player._estimateBufferMemory(mockAudioBuffer);
    const expected = 44100 * 2 * 1.0 * 4; // sampleRate * channels * duration * 4 bytes
    expect(memory).toBe(expected);
  });

  test('_getCurrentQueueMemory sums buffer memory', () => {
    player.addToQueue(mockAudioBuffer);
    player.addToQueue(mockAudioBuffer);
    
    const totalMemory = player._getCurrentQueueMemory();
    const expectedPerBuffer = 44100 * 2 * 1.0 * 4;
    expect(totalMemory).toBe(expectedPerBuffer * 2);
  });

  test('_cleanupBufferPool reduces pool size', () => {
    // Fill buffer pool
    for (let i = 0; i < 10; i++) {
      player.bufferPool.push(mockAudioBuffer);
    }
    
    player._cleanupBufferPool();
    
    expect(player.bufferPool.length).toBe(5); // Should remove half
  });

  test('getPerformanceMetrics returns comprehensive data', () => {
    // Add some test data
    player.performanceMetrics.decodeTime = [10, 20, 30];
    player.performanceMetrics.queueSize = [1, 2, 3];
    player.performanceMetrics.latency = [5, 10, 15];
    player.performanceMetrics.processedChunks = 5;
    player.performanceMetrics.droppedChunks = 1;
    
    const metrics = player.getPerformanceMetrics();
    
    expect(metrics.avgDecodeTime).toBe(20);
    expect(metrics.maxDecodeTime).toBe(30);
    expect(metrics.avgQueueSize).toBe(2);
    expect(metrics.maxQueueSize).toBe(3);
    expect(metrics.avgLatency).toBe(10);
    expect(metrics.maxLatency).toBe(15);
    expect(metrics.processedChunks).toBe(5);
    expect(metrics.droppedChunks).toBe(1);
    expect(metrics.memoryInfo).toBeDefined();
    expect(metrics.bufferPoolSize).toBe(0);
  });

  test('resetPerformanceMetrics clears all data', () => {
    // Add some test data
    player.performanceMetrics.processedChunks = 10;
    player.performanceMetrics.droppedChunks = 2;
    player.performanceMetrics.decodeTime = [1, 2, 3];
    
    player.resetPerformanceMetrics();
    
    expect(player.performanceMetrics.processedChunks).toBe(0);
    expect(player.performanceMetrics.droppedChunks).toBe(0);
    expect(player.performanceMetrics.decodeTime).toEqual([]);
  });

  test('_processAudioQueue uses adaptive intervals', () => {
    jest.useFakeTimers();
    
    // Fill queue to 90% capacity
    const highQueueSize = Math.floor(player.maxQueueSize * 0.9);
    for (let i = 0; i < highQueueSize; i++) {
      player.addToQueue(mockAudioBuffer);
    }
    
    player.startStreamPlayback();
    
    // Should use faster interval (25ms) when queue is full
    jest.advanceTimersByTime(25);
    
    expect(player.audioQueue.length).toBeLessThan(highQueueSize);
    
    jest.useRealTimers();
  });

  test('stopStreamPlayback performs cleanup', () => {
    // Add buffers to queue
    for (let i = 0; i < 5; i++) {
      player.addToQueue(mockAudioBuffer);
    }
    
    player.startStreamPlayback();
    player.stopStreamPlayback();
    
    expect(player.isStreaming).toBe(false);
    expect(player.bufferPool.length).toBe(5); // Buffers moved to pool
    expect(player.audioQueue.length).toBe(0);
  });

  test('performance optimization handles large numbers of chunks', async () => {
    mockAudioContext.decodeAudioData.mockResolvedValue(mockAudioBuffer);
    
    // Process many chunks
    const promises = [];
    for (let i = 0; i < 100; i++) {
      const arrayBuffer = new ArrayBuffer(1000);
      promises.push(player.decodeAudioChunk(arrayBuffer));
    }
    
    await Promise.all(promises);
    
    expect(player.performanceMetrics.processedChunks).toBe(100);
    expect(player.performanceMetrics.decodeTime.length).toBeLessThanOrEqual(100); // Circular buffer
  });

  test('memory management prevents excessive memory usage', () => {
    const largeMockBuffer = {
      duration: 100.0, // Very long buffer
      sampleRate: 44100,
      numberOfChannels: 2
    };
    
    // Try to add buffers that would exceed memory limit
    let addedCount = 0;
    for (let i = 0; i < 20; i++) {
      if (player.addToQueue(largeMockBuffer)) {
        addedCount++;
      }
    }
    
    const totalMemory = player._getCurrentQueueMemory();
    expect(totalMemory).toBeLessThanOrEqual(player.maxQueueMemory);
    expect(addedCount).toBeLessThan(20); // Some should be rejected
  });
});

describe('Basic Audio Playback', () => {
  let mockAudioContext;
  let mockSource;
  let player;

  beforeEach(() => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    mockSource = {
      buffer: null,
      connect: jest.fn(),
      start: jest.fn(),
      onended: null
    };
    
    mockAudioContext = {
      state: 'running',
      currentTime: 0,
      destination: {},
      resume: jest.fn().mockResolvedValue(),
      createBufferSource: jest.fn(() => mockSource),
      decodeAudioData: jest.fn()
    };
    
    global.AudioContext = jest.fn(() => mockAudioContext);
    global.window = { AudioContext: global.AudioContext };
    
    player = new AudioPlayer();
    player.createAudioContext();
  });

  test('playAudioBuffer plays audio successfully', async () => {
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    
    // Simulate successful playback
    const playPromise = player.playAudioBuffer(mockAudioBuffer);
    
    // Verify setup
    expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
    expect(mockSource.buffer).toBe(mockAudioBuffer);
    expect(mockSource.connect).toHaveBeenCalledWith(mockAudioContext.destination);
    expect(mockSource.start).toHaveBeenCalled();
    expect(player.isPlaying).toBe(true);
    
    // Simulate playback completion
    mockSource.onended();
    
    await playPromise;
    expect(player.isPlaying).toBe(false);
  });

  test('playAudioBuffer throws error when AudioContext not initialized', async () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    const uninitializedPlayer = new AudioPlayer();
    
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    
    await expect(uninitializedPlayer.playAudioBuffer(mockAudioBuffer))
      .rejects.toThrow('AudioContext not initialized');
  });

  test('playAudioBuffer throws error for null buffer', async () => {
    await expect(player.playAudioBuffer(null))
      .rejects.toThrow('AudioBuffer is required');
  });

  test('playAudioBuffer resumes suspended context', async () => {
    mockAudioContext.state = 'suspended';
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    
    const playPromise = player.playAudioBuffer(mockAudioBuffer);
    
    expect(mockAudioContext.resume).toHaveBeenCalled();
    
    // Simulate playback completion after a short delay
    setTimeout(() => {
      if (mockSource.onended) {
        mockSource.onended();
      }
    }, 10);
    
    await playPromise;
  });

  test('playAudioBuffer handles playback errors', async () => {
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    mockSource.start.mockImplementation(() => {
      throw new Error('Playback error');
    });
    
    await expect(player.playAudioBuffer(mockAudioBuffer))
      .rejects.toThrow('Playback failed: Playback error');
    
    expect(player.isPlaying).toBe(false);
  });

  test('playAudioBuffer updates playback state correctly', async () => {
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    mockAudioContext.currentTime = 5.5;
    
    expect(player.isPlaying).toBe(false);
    expect(player.currentPlaybackTime).toBe(0);
    
    const playPromise = player.playAudioBuffer(mockAudioBuffer);
    
    expect(player.isPlaying).toBe(true);
    expect(player.currentPlaybackTime).toBe(5.5);
    
    // Simulate playback completion
    mockSource.onended();
    await playPromise;
    
    expect(player.isPlaying).toBe(false);
  });

  test('playAudioBuffer calls onPlaybackComplete callback', async () => {
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    const mockCallback = jest.fn();
    player.onPlaybackComplete = mockCallback;
    
    const playPromise = player.playAudioBuffer(mockAudioBuffer);
    
    // Simulate playback completion
    mockSource.onended();
    await playPromise;
    
    expect(mockCallback).toHaveBeenCalled();
  });

  test('playAudioBuffer works without callback', async () => {
    const mockAudioBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    player.onPlaybackComplete = null;
    
    const playPromise = player.playAudioBuffer(mockAudioBuffer);
    
    // Simulate playback completion
    mockSource.onended();
    await playPromise;
    
    expect(player.isPlaying).toBe(false);
  });
});

describe('Continuous Stream Playback', () => {
  let mockAudioContext;
  let mockSources;
  let player;
  let sourceIndex;

  beforeEach(() => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    sourceIndex = 0;
    mockSources = [];
    
    // Create multiple mock sources
    for (let i = 0; i < 5; i++) {
      mockSources.push({
        buffer: null,
        connect: jest.fn(),
        start: jest.fn(),
        stop: jest.fn(),
        onended: null
      });
    }
    
    mockAudioContext = {
      state: 'running',
      currentTime: 0,
      destination: {},
      resume: jest.fn().mockResolvedValue(),
      createBufferSource: jest.fn(() => {
        const source = mockSources[sourceIndex % mockSources.length];
        sourceIndex++;
        return source;
      }),
      decodeAudioData: jest.fn()
    };
    
    global.AudioContext = jest.fn(() => mockAudioContext);
    global.window = { AudioContext: global.AudioContext };
    
    player = new AudioPlayer();
    player.createAudioContext();
    
    // Mock setTimeout for testing
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('startStreamPlayback initializes streaming', () => {
    expect(player.isStreaming).toBe(false);
    expect(player.nextPlaybackTime).toBe(0);
    
    player.startStreamPlayback();
    
    expect(player.isStreaming).toBe(true);
    expect(player.nextPlaybackTime).toBe(0); // currentTime is 0
  });

  test('startStreamPlayback throws error when AudioContext not initialized', () => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    const uninitializedPlayer = new AudioPlayer();
    
    expect(() => {
      uninitializedPlayer.startStreamPlayback();
    }).toThrow('AudioContext not initialized');
  });

  test('startStreamPlayback does nothing if already streaming', () => {
    player.isStreaming = true;
    player.nextPlaybackTime = 5.0;
    
    player.startStreamPlayback();
    
    expect(player.nextPlaybackTime).toBe(5.0); // Should not reset
  });

  test('stopStreamPlayback stops streaming and clears sources', () => {
    // Start streaming and add some sources
    player.startStreamPlayback();
    player.activeSources = [mockSources[0], mockSources[1]];
    
    player.stopStreamPlayback();
    
    expect(player.isStreaming).toBe(false);
    expect(player.nextPlaybackTime).toBe(0);
    expect(player.activeSources).toHaveLength(0);
    expect(mockSources[0].stop).toHaveBeenCalled();
    expect(mockSources[1].stop).toHaveBeenCalled();
  });

  test('stopStreamPlayback handles source stop errors gracefully', () => {
    player.startStreamPlayback();
    
    // Mock source that throws error on stop
    const errorSource = { stop: jest.fn(() => { throw new Error('Stop failed'); }) };
    player.activeSources = [errorSource];
    
    // Should not throw
    expect(() => player.stopStreamPlayback()).not.toThrow();
    expect(player.activeSources).toHaveLength(0);
  });

  test('_processAudioQueue processes queued audio buffers', () => {
    const mockBuffer1 = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    const mockBuffer2 = { duration: 1.5, sampleRate: 44100, numberOfChannels: 2 };
    
    player.addToQueue(mockBuffer1);
    player.addToQueue(mockBuffer2);
    
    expect(player.getQueueSize()).toBe(2);
    
    player.startStreamPlayback();
    
    // Process first buffer - the initial call happens immediately
    jest.advanceTimersByTime(1);
    
    expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
    expect(mockSources[0].buffer).toBe(mockBuffer1);
    expect(mockSources[0].start).toHaveBeenCalled();
    expect(player.getQueueSize()).toBe(1); // One buffer consumed
  });

  test('_scheduleAudioBuffer schedules audio with precise timing', () => {
    const mockBuffer = { duration: 2.0, sampleRate: 44100, numberOfChannels: 2 };
    mockAudioContext.currentTime = 5.0;
    player.nextPlaybackTime = 6.0;
    
    player._scheduleAudioBuffer(mockBuffer);
    
    expect(mockSources[0].buffer).toBe(mockBuffer);
    expect(mockSources[0].connect).toHaveBeenCalledWith(mockAudioContext.destination);
    expect(mockSources[0].start).toHaveBeenCalledWith(6.0); // Uses nextPlaybackTime
    expect(player.nextPlaybackTime).toBe(8.0); // 6.0 + 2.0 duration
    expect(player.activeSources).toContain(mockSources[0]);
  });

  test('_scheduleAudioBuffer handles timing gaps correctly', () => {
    const mockBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    mockAudioContext.currentTime = 10.0;
    player.nextPlaybackTime = 8.0; // Behind current time
    
    player._scheduleAudioBuffer(mockBuffer);
    
    expect(mockSources[0].start).toHaveBeenCalledWith(10.0); // Uses currentTime
    expect(player.nextPlaybackTime).toBe(11.0); // 10.0 + 1.0 duration
  });

  test('_scheduleAudioBuffer removes source from active list on end', () => {
    const mockBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    
    player._scheduleAudioBuffer(mockBuffer);
    
    expect(player.activeSources).toContain(mockSources[0]);
    
    // Simulate source ending
    mockSources[0].onended();
    
    expect(player.activeSources).not.toContain(mockSources[0]);
  });

  test('_scheduleAudioBuffer handles errors gracefully', () => {
    const mockBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    mockSources[0].start.mockImplementation(() => {
      throw new Error('Start failed');
    });
    
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    // Should not throw
    expect(() => player._scheduleAudioBuffer(mockBuffer)).not.toThrow();
    expect(consoleSpy).toHaveBeenCalledWith('Failed to schedule audio buffer:', expect.any(Error));
    
    consoleSpy.mockRestore();
  });

  test('streaming processes multiple buffers continuously', () => {
    const buffers = [
      { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 },
      { duration: 1.5, sampleRate: 44100, numberOfChannels: 2 },
      { duration: 0.5, sampleRate: 44100, numberOfChannels: 2 }
    ];
    
    buffers.forEach(buffer => player.addToQueue(buffer));
    
    player.startStreamPlayback();
    
    // Process all buffers
    jest.advanceTimersByTime(200); // Multiple 50ms intervals
    
    expect(mockAudioContext.createBufferSource).toHaveBeenCalledTimes(3);
    expect(player.getQueueSize()).toBe(0); // All buffers consumed
    expect(player.activeSources).toHaveLength(3);
  });

  test('streaming stops processing when isStreaming is false', () => {
    const mockBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    player.addToQueue(mockBuffer);
    
    player.startStreamPlayback();
    
    // Reset the mock to count calls after stopping
    mockAudioContext.createBufferSource.mockClear();
    
    player.stopStreamPlayback();
    
    jest.advanceTimersByTime(100);
    
    // Should not process any more buffers after stopping
    expect(mockAudioContext.createBufferSource).not.toHaveBeenCalled();
  });
});

describe('Error Recovery & User Experience', () => {
  let mockAudioContext;
  let player;

  beforeEach(() => {
    const { AudioPlayer } = require('../src/audioPlayer.js');
    
    mockAudioContext = {
      state: 'running',
      currentTime: 0,
      destination: {},
      resume: jest.fn().mockResolvedValue(),
      decodeAudioData: jest.fn(),
      createBufferSource: jest.fn()
    };
    
    global.AudioContext = jest.fn(() => mockAudioContext);
    global.window = { AudioContext: global.AudioContext };
    
    // Create fresh mock element for each test
    const mockElement = {
      id: '',
      style: { cssText: '' },
      addEventListener: jest.fn(),
      remove: jest.fn(),
      innerHTML: ''
    };
    
    // Create fresh mock functions for each test
    const createElementMock = jest.fn(() => mockElement);
    const appendChildMock = jest.fn();
    
    global.document = {
      createElement: createElementMock,
      body: { appendChild: appendChildMock }
    };
    
    // Store references for tests
    global.mockElement = mockElement;
    global.mockCreateElement = createElementMock;
    global.mockAppendChild = appendChildMock;
    
    player = new AudioPlayer();
    player.createAudioContext();
    
    // Reset user gesture state for each test
    player.userGestureRequested = false;
  });

  test('automatic retry for failed audio decoding works', async () => {
    const mockAudioBuffer = { sampleRate: 44100, numberOfChannels: 2, duration: 1.0 };
    
    // Fail first two attempts, succeed on third
    mockAudioContext.decodeAudioData
      .mockRejectedValueOnce(new Error('Network error'))
      .mockRejectedValueOnce(new Error('Temporary failure'))
      .mockResolvedValueOnce(mockAudioBuffer);
    
    const arrayBuffer = new ArrayBuffer(1000);
    const result = await player.decodeAudioChunk(arrayBuffer);
    
    expect(mockAudioContext.decodeAudioData).toHaveBeenCalledTimes(3);
    expect(result).toBe(mockAudioBuffer);
    expect(player.consecutiveFailures).toBe(0); // Reset on success
  });

  test('graceful handling of corrupted audio data', async () => {
    // Mock decode that returns invalid buffer
    const invalidBuffer = { sampleRate: 0, numberOfChannels: 0, duration: -1 };
    mockAudioContext.decodeAudioData.mockResolvedValue(invalidBuffer);
    
    const arrayBuffer = new ArrayBuffer(1000);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow('Kan audio niet decoderen');
    
    expect(player.performanceMetrics.droppedChunks).toBe(1);
  });

  test('recovery from AudioContext suspension', async () => {
    mockAudioContext.state = 'suspended';
    mockAudioContext.resume.mockImplementation(() => {
      // Simulate successful resume
      mockAudioContext.state = 'running';
      return Promise.resolve();
    });
    
    const mockAudioBuffer = { sampleRate: 44100, numberOfChannels: 2, duration: 1.0 };
    mockAudioContext.decodeAudioData.mockResolvedValue(mockAudioBuffer);
    
    const arrayBuffer = new ArrayBuffer(1000);
    const result = await player.decodeAudioChunk(arrayBuffer);
    
    expect(mockAudioContext.resume).toHaveBeenCalled();
    expect(result).toBe(mockAudioBuffer);
  });

  test('AudioContext suspension requires user gesture', async () => {
    mockAudioContext.state = 'suspended';
    mockAudioContext.resume.mockImplementation(() => {
      // Context remains suspended, simulating need for user gesture
      return Promise.resolve();
    });
    
    const arrayBuffer = new ArrayBuffer(1000);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow('Audio systeem geblokkeerd - klik ergens op de pagina');
    
    expect(player.userGestureRequested).toBe(true);
  });

  test('user-friendly error reporting works', async () => {
    const mockCallback = jest.fn();
    player.onError = mockCallback;
    
    const networkError = new Error('Network failed');
    networkError.name = 'NetworkError';
    mockAudioContext.decodeAudioData.mockRejectedValue(networkError);
    
    const arrayBuffer = new ArrayBuffer(1000);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow('Netwerkfout tijdens audio verwerking');
    
    expect(mockCallback).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: 'decode',
        error: 'Netwerkfout tijdens audio verwerking',
        suggestion: 'Controleer uw internetverbinding en herlaad de pagina',
        recoverable: true
      })
    );
  });

  test('recovery mode is activated after consecutive failures', async () => {
    player.consecutiveFailures = 15; // Above threshold
    
    mockAudioContext.decodeAudioData.mockRejectedValue(new Error('Persistent failure'));
    
    const arrayBuffer = new ArrayBuffer(1000);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow();
    
    expect(player.recoveryMode).toBe(true);
    expect(player.maxQueueSize).toBeLessThan(50); // Reduced from original
  });

  test('recovery mode exits automatically after timeout', () => {
    jest.useFakeTimers();
    
    player._enterRecoveryMode();
    expect(player.recoveryMode).toBe(true);
    
    // Advance time by 30 seconds
    jest.advanceTimersByTime(30000);
    
    expect(player.recoveryMode).toBe(false);
    expect(player.maxQueueSize).toBe(50); // Restored
    
    jest.useRealTimers();
  });

  test('error callback is called for critical errors', async () => {
    const mockCallback = jest.fn();
    player.onError = mockCallback;
    
    // Uninitialize context to trigger critical error
    player.audioContext = null;
    
    const arrayBuffer = new ArrayBuffer(1000);
    
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow();
    
    expect(mockCallback).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: 'context',
        recoverable: false
      })
    );
  });

  test('recovery callback is called after successful recovery', async () => {
    const mockRecoveryCallback = jest.fn();
    player.onRecovery = mockRecoveryCallback;
    
    player.consecutiveFailures = 3;
    
    const mockAudioBuffer = { sampleRate: 44100, numberOfChannels: 2, duration: 1.0 };
    mockAudioContext.decodeAudioData.mockResolvedValue(mockAudioBuffer);
    
    const arrayBuffer = new ArrayBuffer(1000);
    await player.decodeAudioChunk(arrayBuffer);
    
    expect(mockRecoveryCallback).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: 'decode',
        message: 'decode hersteld na 3 fouten'
      })
    );
  });

  test('user gesture overlay is created for suspended context', () => {
    // Verify the reset worked
    expect(player.userGestureRequested).toBe(false);
    
    player._requestUserGesture();
    
    expect(global.mockCreateElement).toHaveBeenCalledWith('div');
    expect(global.mockElement.id).toBe('audio-gesture-overlay');
    expect(global.mockElement.style.cssText).toContain('position: fixed');
    expect(global.mockElement.innerHTML).toContain('Audio Activatie Vereist');
    expect(global.mockAppendChild).toHaveBeenCalledWith(global.mockElement);
    expect(player.userGestureRequested).toBe(true);
  });

  test('emergency cleanup is performed under memory pressure', () => {
    // Setup memory pressure conditions
    global.performance = {
      memory: {
        usedJSHeapSize: 90 * 1024 * 1024,
        jsHeapSizeLimit: 100 * 1024 * 1024
      }
    };
    
    // Fill queue
    const mockBuffer = { duration: 1.0, sampleRate: 44100, numberOfChannels: 2 };
    for (let i = 0; i < player.maxQueueSize; i++) {
      player.addToQueue(mockBuffer);
    }
    
    // Add active sources
    player.activeSources = [
      { stop: jest.fn() },
      { stop: jest.fn() },
      { stop: jest.fn() }
    ];
    
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    
    player._performEmergencyCleanup();
    
    expect(consoleSpy).toHaveBeenCalledWith(
      'AudioPlayer: Performing emergency cleanup due to memory pressure'
    );
    expect(player.audioQueue.length).toBeLessThanOrEqual(5);
    expect(player.bufferPool.length).toBe(0);
    expect(player.activeSources.length).toBe(0);
    
    consoleSpy.mockRestore();
  });

  test('quality change callback is called when quality changes', () => {
    const mockCallback = jest.fn();
    player.onQualityChange = mockCallback;
    
    player._updatePlaybackQuality('poor');
    
    expect(mockCallback).toHaveBeenCalledWith('poor');
  });

  test('playback quality assessment works correctly', () => {
    // Set up performance metrics for "Fair" quality assessment
    player.performanceMetrics.processedChunks = 60;
    player.performanceMetrics.droppedChunks = 40; // 40% drop rate (severe)
    player.performanceMetrics.latency = [120, 140, 160]; // Average 140ms (high latency)
    
    const quality = player.getPlaybackQuality();
    
    expect(quality.overall).toBe('Fair');
    expect(quality.latency).toBe('Fair');
    expect(quality.stability).toBe('Poor'); // Due to high drop rate
    expect(quality.recommendations).toContain('Hoge drop rate - controleer internetverbinding');
  });

  test('health report provides comprehensive diagnostics', () => {
    // Add some test data
    player.performanceMetrics.processedChunks = 50;
    player.performanceMetrics.droppedChunks = 5;
    player.addToQueue({ duration: 1.0, sampleRate: 44100, numberOfChannels: 2 });
    player.activeSources = [{}];
    
    const report = player.getHealthReport();
    
    expect(report.overall).toBeDefined();
    expect(report.audioContext.state).toBe('running');
    expect(report.playback.queueSize).toBe(1);
    expect(report.performance.processedChunks).toBe(50);
    expect(report.memory.queueMemory).toBeGreaterThan(0);
    expect(report.errors.successRate).toBe('90.91%');
    expect(report.diagnostics.webAudioSupport).toBe(true);
    expect(report.troubleshooting).toBeInstanceOf(Array);
  });

  test('troubleshooting recommendations are context-aware', () => {
    // Create various problem conditions
    player.audioContext = null;
    player.performanceMetrics.droppedChunks = 10;
    player.consecutiveFailures = 8;
    
    const steps = player._getTroubleshootingSteps();
    
    expect(steps).toContain('Initialize AudioContext by calling createAudioContext()');
    expect(steps).toContain('Hoge drop rate - controleer internetverbinding');
    expect(steps).toContain('Herhaalde fouten - herstart audio systeem');
  });

  test('error history is maintained correctly', () => {
    const error1 = new Error('First error');
    error1.name = 'NetworkError';
    const error2 = new Error('Second error');
    error2.name = 'DataError';
    
    player._logError(error1, 'decode');
    player._logError(error2, 'playback');
    
    const recentErrors = player._getRecentErrors();
    
    expect(recentErrors).toHaveLength(2);
    expect(recentErrors[0].operation).toBe('decode');
    expect(recentErrors[1].operation).toBe('playback');
    expect(recentErrors[0].recoverable).toBe(true); // NetworkError is recoverable
  });

  test('callback errors do not break error handling', async () => {
    // Set up callback that throws error
    player.onError = jest.fn(() => {
      throw new Error('Callback error');
    });
    
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
    
    // Trigger an error
    const arrayBuffer = new ArrayBuffer(1000);
    await expect(player.decodeAudioChunk(arrayBuffer))
      .rejects.toThrow();
    
    // Error callback should have been attempted and warning logged
    expect(player.onError).toHaveBeenCalled();
    expect(consoleSpy).toHaveBeenCalledWith('Error callback failed:', expect.any(Error));
    
    consoleSpy.mockRestore();
  });
});