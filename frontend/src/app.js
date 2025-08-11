/**
 * Main Application Entry Point
 * Initializes the application and handles browser compatibility
 */

// Make functions global for testing
if (typeof global !== 'undefined') {
    // Import modules for testing
    const ui = require('./ui.js');
    const connection = require('./connection.js');
    const config = require('./config.js');
    
    global.startBroadcast = ui.startBroadcast;
    global.joinListener = ui.joinListener;
    global.updateStatus = ui.updateStatus;
    global.connectWebSocket = connection.connectWebSocket;
    global.disconnectWebSocket = connection.disconnectWebSocket;
    global.enableButtons = ui.enableButtons;
}

// DOM Ready setup
document.addEventListener('DOMContentLoaded', function() {
    // Check browser compatibility (graceful fallback)
    if (window.AppUtils && window.AppUtils.showCompatibilityWarning) {
        window.AppUtils.showCompatibilityWarning();
    }
    
    // Initialize UI (graceful fallback)
    if (window.AppUI && window.AppUI.initializeUI) {
        window.AppUI.initializeUI();
    }
    
    console.log('Live Speech Translation App initialized');
    if (window.AppConfig) {
        console.log('Environment:', window.AppConfig.getEnvironment());
        console.log('WebSocket URL:', window.AppConfig.getWebSocketURL());
    }
});