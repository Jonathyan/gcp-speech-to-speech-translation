// Configuration management
const CONFIG = {
  // WebSocket URLs
  WEBSOCKET_URL: {
    development: 'ws://localhost:8000/ws',
    production: 'wss://your-domain.com/ws'
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
  
  // Audio settings
  AUDIO: {
    CHUNK_INTERVAL_MS: 250,
    MAX_CHUNK_SIZE: 100 * 1024, // 100KB
    AUDIO_CONSTRAINTS: {
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    },
    SUPPORTED_MIME_TYPES: ['audio/webm', 'audio/mp4', 'audio/wav']
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
    intervalMs: CONFIG.AUDIO.CHUNK_INTERVAL_MS,
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