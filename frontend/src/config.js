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

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CONFIG, getEnvironment, getWebSocketURL };
}

// Global for browser
if (typeof window !== 'undefined') {
  window.AppConfig = { CONFIG, getEnvironment, getWebSocketURL };
}