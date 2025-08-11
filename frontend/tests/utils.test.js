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

  test('showCompatibilityWarning shows audio warnings', () => {
    const utils = require('../src/utils.js');
    
    // Ensure no audio support (reset globals)
    delete global.MediaRecorder;
    delete global.navigator;
    delete global.WebSocket;
    
    // Mock DOM
    const mockWarning = { style: {}, innerHTML: '' };
    const mockBody = {
      insertBefore: jest.fn(),
      firstChild: {}
    };
    const mockCreateElement = jest.fn(() => mockWarning);
    global.document = {
      createElement: mockCreateElement,
      body: mockBody,
      addEventListener: jest.fn(),
      querySelector: jest.fn()
    };
    
    // Verify no support is detected
    const support = utils.checkBrowserSupport();
    expect(support.webSocket).toBe(false);
    expect(support.getUserMedia).toBe(false);
    expect(support.mediaRecorder).toBe(false);
    
    // Test with no audio support
    utils.showCompatibilityWarning();
    
    expect(mockCreateElement).toHaveBeenCalledWith('div');
    expect(mockBody.insertBefore).toHaveBeenCalled();
    expect(mockWarning.innerHTML).toContain('Browser Compatibiliteit');
  });
});