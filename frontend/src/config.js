// Configuration management
const CONFIG = {
  // WebSocket URLs
  WEBSOCKET_URL: {
    development: 'ws://localhost:8000',
    production: 'wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app'
  },
  
  // Connection settings
  CONNECTION: {
    maxRetries: 3,
    retryDelayBase: 1000, // Base delay in ms (exponential backoff)
    connectionTimeout: 5000
  },
  
  // UI settings
  UI: {
    statusUpdateDelay: 100,
    buttonDebounceDelay: 300
  },
  
  // Audio settings - Phase 3: Real-time optimized for speech translation
  AUDIO: {
    CHUNK_INTERVAL_MS: 250,  // 250ms - optimal for real-time translation (8x faster than before)
    CHUNK_SIZE: 2048,        // 2KB chunks for lower latency processing
    MAX_CHUNK_SIZE: 150 * 1024, // 150KB - larger chunks for WAV
    AUDIO_CONSTRAINTS: {
      audio: {
        sampleRate: 16000,        // Phase 2: Optimal for Google Cloud STT
        channelCount: 1,          // Mono for optimal recognition
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    },
    // Phase 2: WAV first for Professional Audio Recorder, WebM fallback for MediaRecorder
    SUPPORTED_MIME_TYPES: ['audio/wav', 'audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'],
    // Phase 2: Enable Web Audio API by default
    USE_WEB_AUDIO_API: true
  }
};

// Environment detection
function getEnvironment() {
  if (typeof window !== 'undefined') {
    return window.location.hostname === 'localhost' ? 'development' : 'production';
  }
  return 'development';
}

// Get WebSocket URL for current environment
function getWebSocketURL() {
  const env = getEnvironment();
  return CONFIG.WEBSOCKET_URL[env];
}

/**
 * Get best supported audio format
 * @returns {string} Best available MIME type
 */
function getBestAudioFormat() {
  if (typeof MediaRecorder === 'undefined') {
    return CONFIG.AUDIO.SUPPORTED_MIME_TYPES[0]; // Fallback
  }
  
  for (const mimeType of CONFIG.AUDIO.SUPPORTED_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }
  
  // Final fallback - return first type even if not supported
  return CONFIG.AUDIO.SUPPORTED_MIME_TYPES[0];
}

/**
 * Get audio constraints for getUserMedia
 * @returns {object} Audio constraints
 */
function getAudioConstraints() {
  return CONFIG.AUDIO.AUDIO_CONSTRAINTS;
}

/**
 * Get audio chunk configuration
 * @returns {object} Chunk timing and size limits
 */
function getAudioChunkConfig() {
  return {
    chunkIntervalMs: CONFIG.AUDIO.CHUNK_INTERVAL_MS,
    chunkSize: CONFIG.AUDIO.CHUNK_SIZE,
    maxSize: CONFIG.AUDIO.MAX_CHUNK_SIZE
  };
}

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { 
    CONFIG, 
    getEnvironment, 
    getWebSocketURL, 
    getBestAudioFormat,
    getAudioConstraints,
    getAudioChunkConfig
  };
}

// Global for browser
if (typeof window !== 'undefined') {
  window.AppConfig = { 
    CONFIG, 
    getEnvironment, 
    getWebSocketURL, 
    getBestAudioFormat,
    getAudioConstraints,
    getAudioChunkConfig
  };
}