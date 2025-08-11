/**
 * WebSocket Connection Management Module
 * Handles WebSocket connections, retries, and error handling
 */

// Global connection state
let currentWebSocket = null;
let retryCount = 0;

/**
 * Establish WebSocket connection with retry logic
 * @param {string} url - WebSocket URL
 * @param {string} mode - Connection mode ('broadcast' or 'listener')
 */
function connectWebSocket(url, mode) {
  const config = window.AppConfig.CONFIG.CONNECTION;
  
  // Clean up existing connection
  if (currentWebSocket) {
    currentWebSocket.close();
    currentWebSocket = null;
  }
  
  try {
    currentWebSocket = new WebSocket(url);
    
    currentWebSocket.onopen = function() {
      retryCount = 0;
      handleConnectionSuccess(mode);
    };
    
    currentWebSocket.onclose = function(event) {
      currentWebSocket = null;
      if (event.wasClean) {
        handleCleanDisconnect();
      } else {
        handleConnectionError(url, mode);
      }
    };
    
    currentWebSocket.onerror = function() {
      handleConnectionError(url, mode);
    };
    
    currentWebSocket.onmessage = function(event) {
      handleIncomingMessage(event.data);
    };
    
  } catch (error) {
    handleConnectionError(url, mode);
  }
}

/**
 * Handle successful connection
 * @param {string} mode - Connection mode
 */
function handleConnectionSuccess(mode) {
  const message = mode === 'broadcast' 
    ? 'Verbonden - Klaar om uit te zenden'
    : 'Verbonden - Luisteren...';
  
  window.AppUI.updateStatus(message);
  window.AppUI.enableButtons(false);
}

/**
 * Handle clean disconnection
 */
function handleCleanDisconnect() {
  window.AppUI.updateStatus('Verbinding gesloten');
  window.AppUI.enableButtons(true);
}

/**
 * Handle connection errors with retry logic
 * @param {string} url - WebSocket URL
 * @param {string} mode - Connection mode
 */
function handleConnectionError(url, mode) {
  const config = window.AppConfig.CONFIG.CONNECTION;
  
  if (retryCount < config.maxRetries) {
    retryCount++;
    const delay = Math.pow(2, retryCount) * config.retryDelayBase;
    
    window.AppUI.updateStatus(`Verbinding mislukt - Opnieuw proberen in ${delay/1000}s...`);
    
    setTimeout(() => {
      window.AppUI.updateStatus('Opnieuw verbinden...');
      connectWebSocket(url, mode);
    }, delay);
  } else {
    window.AppUI.updateStatus('Verbinding mislukt - Controleer of de server draait');
    retryCount = 0;
    window.AppUI.enableButtons(true);
  }
}

/**
 * Handle incoming WebSocket messages
 * @param {string} data - Message data
 */
function handleIncomingMessage(data) {
  console.log('Message received:', data);
  // Future: Handle audio data processing
}

/**
 * Disconnect WebSocket cleanly
 */
function disconnectWebSocket() {
  if (currentWebSocket) {
    currentWebSocket.close();
    currentWebSocket = null;
  }
  window.AppUI.enableButtons(true);
  window.AppUI.updateStatus('Ready');
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { connectWebSocket, disconnectWebSocket };
}

if (typeof window !== 'undefined') {
  window.AppConnection = { connectWebSocket, disconnectWebSocket };
}