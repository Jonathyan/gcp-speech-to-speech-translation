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
    console.log('DOM loaded, initializing app...');
    
    // Check browser compatibility (graceful fallback)
    if (window.AppUtils && window.AppUtils.showCompatibilityWarning) {
        console.log('Running compatibility check...');
        window.AppUtils.showCompatibilityWarning();
    } else {
        console.warn('AppUtils not available');
    }
    
    // Initialize UI (graceful fallback)
    if (window.AppUI && window.AppUI.initializeUI) {
        console.log('Initializing UI...');
        window.AppUI.initializeUI();
    } else {
        console.error('AppUI not available - buttons will remain disabled');
        // Fallback: enable buttons directly
        console.log('Attempting direct button enablement...');
        const startButton = document.getElementById('start-broadcast');
        const listenButton = document.getElementById('join-listener');
        if (startButton) {
            startButton.disabled = false;
            console.log('Enabled start-broadcast button');
        }
        if (listenButton) {
            listenButton.disabled = false;
            console.log('Enabled join-listener button');
        }
    }
    
    console.log('Live Speech Translation App initialized');
    if (window.AppConfig) {
        console.log('Environment:', window.AppConfig.getEnvironment());
        console.log('WebSocket URL:', window.AppConfig.getWebSocketURL());
    } else {
        console.error('AppConfig not available');
    }
    
    // Additional debug info
    console.log('Available globals:', {
        AppConfig: !!window.AppConfig,
        AppUI: !!window.AppUI,
        AppUtils: !!window.AppUtils,
        AppConnection: !!window.AppConnection,
        AppAudio: !!window.AppAudio,
        WAVEncoder: !!window.WAVEncoder,
        ProfessionalAudioRecorder: !!window.ProfessionalAudioRecorder
    });
});