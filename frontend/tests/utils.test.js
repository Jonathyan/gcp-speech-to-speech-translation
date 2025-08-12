describe('Audio Support Detection', () => {
  beforeEach(() => {
    // Reset global mocks
    delete global.MediaRecorder;
    delete global.navigator;
    delete global.AudioContext;
    delete global.webkitAudioContext;
  });

  test('isMediaRecorderSupported detects MediaRecorder support', () => {
    const utils = require('../src/utils.js');
    
    // Test when MediaRecorder is not supported
    expect(utils.isMediaRecorderSupported()).toBe(false);
    
    // Test when MediaRecorder is supported
    global.MediaRecorder = function() {};
    expect(utils.isMediaRecorderSupported()).toBe(true);
  });

  test('isGetUserMediaSupported detects getUserMedia support', () => {
    const utils = require('../src/utils.js');
    
    // Test when getUserMedia is not supported
    expect(utils.isGetUserMediaSupported()).toBe(false);
    
    // Test when getUserMedia is supported
    global.navigator = {
      mediaDevices: {
        getUserMedia: jest.fn()
      }
    };
    expect(utils.isGetUserMediaSupported()).toBe(true);
  });

  test('isWebAudioSupported detects Web Audio API support', () => {
    const utils = require('../src/utils.js');
    
    // Test when Web Audio API is not supported
    expect(utils.isWebAudioSupported()).toBe(false);
    
    // Test when AudioContext is supported
    global.AudioContext = function() {};
    expect(utils.isWebAudioSupported()).toBe(true);
    
    // Reset and test webkit fallback
    delete global.AudioContext;
    global.webkitAudioContext = function() {};
    expect(utils.isWebAudioSupported()).toBe(true);
  });

  test('checkAudioSupport returns comprehensive audio capabilities', () => {
    const utils = require('../src/utils.js');
    
    // Test with no audio support
    let support = utils.checkAudioSupport();
    expect(support).toEqual({
      mediaRecorder: false,
      getUserMedia: false,
      webAudio: false
    });
    
    // Test with full audio support
    global.MediaRecorder = function() {};
    global.navigator = {
      mediaDevices: {
        getUserMedia: jest.fn()
      }
    };
    global.AudioContext = function() {};
    
    support = utils.checkAudioSupport();
    expect(support).toEqual({
      mediaRecorder: true,
      getUserMedia: true,
      webAudio: true
    });
  });

  test('checkBrowserSupport includes audio capabilities', () => {
    const utils = require('../src/utils.js');
    
    // Mock basic browser features
    global.WebSocket = function() {};
    global.Storage = function() {};
    global.document = {
      addEventListener: jest.fn(),
      querySelector: jest.fn()
    };
    
    const support = utils.checkBrowserSupport();
    expect(support).toHaveProperty('mediaRecorder');
    expect(support).toHaveProperty('getUserMedia');
    expect(support).toHaveProperty('webAudio');
    expect(support).toHaveProperty('webSocket');
  });

  test('showCompatibilityWarning includes Web Audio API warnings', () => {
    const utils = require('../src/utils.js');
    
    // Test that Web Audio API is included in browser support check
    const support = utils.checkBrowserSupport();
    expect(support).toHaveProperty('webAudio');
    
    // Test with no Web Audio support
    delete global.AudioContext;
    delete global.webkitAudioContext;
    
    const supportWithoutWebAudio = utils.checkAudioSupport();
    expect(supportWithoutWebAudio.webAudio).toBe(false);
    
    // Test with Web Audio support
    global.AudioContext = function() {};
    const supportWithWebAudio = utils.checkAudioSupport();
    expect(supportWithWebAudio.webAudio).toBe(true);
  });
});