/**
 * UI Management Module
 * Handles DOM manipulation, button states, and user interactions
 */

/**
 * Update status message
 * @param {string} message - Status message to display
 */
function updateStatus(message) {
  const statusDiv = document.getElementById('status');
  if (statusDiv) {
    statusDiv.textContent = message;
  }
}

/**
 * Enable/disable buttons based on connection state
 * @param {boolean} enabled - Whether buttons should be enabled
 */
function enableButtons(enabled) {
  const startButton = document.getElementById('start-broadcast');
  const listenButton = document.getElementById('join-listener');
  const disconnectButton = document.getElementById('disconnect');
  
  if (startButton) startButton.disabled = !enabled;
  if (listenButton) listenButton.disabled = !enabled;
  if (disconnectButton) disconnectButton.disabled = enabled;
}

/**
 * Handle start broadcast button click
 */
function startBroadcast() {
  updateStatus('Verbinden...');
  const url = window.AppConfig.getWebSocketURL();
  window.AppConnection.connectWebSocket(url, 'broadcast');
}

/**
 * Handle join listener button click
 */
function joinListener() {
  updateStatus('Verbinden als luisteraar...');
  const url = window.AppConfig.getWebSocketURL();
  window.AppConnection.connectWebSocket(url, 'listener');
}

/**
 * Initialize UI event handlers
 */
function initializeUI() {
  const startButton = document.getElementById('start-broadcast');
  const listenButton = document.getElementById('join-listener');
  const disconnectButton = document.getElementById('disconnect');
  
  // Setup initial state
  if (startButton) startButton.disabled = false;
  if (listenButton) listenButton.disabled = false;
  if (disconnectButton) disconnectButton.disabled = true;
  
  // Attach event handlers
  if (startButton) startButton.addEventListener('click', startBroadcast);
  if (listenButton) listenButton.addEventListener('click', joinListener);
  if (disconnectButton) {
    disconnectButton.addEventListener('click', window.AppConnection.disconnectWebSocket);
  }
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { updateStatus, enableButtons, startBroadcast, joinListener, initializeUI };
}

if (typeof window !== 'undefined') {
  window.AppUI = { updateStatus, enableButtons, startBroadcast, joinListener, initializeUI };
}