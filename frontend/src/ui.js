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

// Global recording state
let currentRecorder = null;
let recordingStream = null;

/**
 * Handle test microphone button click
 */
async function testMicrophone() {
  updateStatus('Microfoon toegang aanvragen...');
  
  const result = await window.AppAudio.requestMicrophoneAccess();
  
  if (result.success) {
    updateStatus('✅ Microfoon toegang verkregen!');
    // Stop the stream after 2 seconds
    setTimeout(() => {
      window.AppAudio.stopAudioStream(result.stream);
      updateStatus('Microfoon test voltooid');
    }, 2000);
  } else {
    updateStatus(`❌ Microfoon fout: ${result.error}`);
  }
}

/**
 * Handle start recording button click
 */
async function startRecording() {
  if (currentRecorder && currentRecorder.isRecording) {
    // Stop recording
    currentRecorder.stop();
    window.AppAudio.stopAudioStream(recordingStream);
    currentRecorder = null;
    recordingStream = null;
    
    updateStatus('Opname gestopt');
    document.getElementById('start-recording').textContent = 'Start Opname';
    return;
  }
  
  updateStatus('Microfoon toegang aanvragen voor opname...');
  
  const result = await window.AppAudio.requestMicrophoneAccess();
  
  if (result.success) {
    recordingStream = result.stream;
    
    try {
      currentRecorder = new window.AppAudio.AudioRecorder(result.stream, {
        onDataAvailable: async (data) => {
          console.log('Audio chunk received:', data.size, 'bytes');
          
          try {
            // Convert and validate audio chunk
            const arrayBuffer = await window.AppAudio.convertAudioChunk(data);
            const validation = window.AppAudio.validateAudioChunk(arrayBuffer);
            
            if (validation.isValid) {
              updateStatus(`🔴 Opname actief - ${validation.size} bytes (geldig)`);
              console.log('Valid audio chunk:', validation.size, 'bytes');
            } else {
              updateStatus(`⚠️ Opname - ${validation.error}`);
              console.warn('Invalid audio chunk:', validation.error);
            }
          } catch (error) {
            updateStatus(`❌ Audio conversie fout: ${error.message}`);
            console.error('Audio conversion error:', error);
          }
        },
        onError: (error) => {
          console.error('Recording error:', error);
          updateStatus(`❌ Opname fout: ${error.message}`);
        }
      });
      
      currentRecorder.start();
      updateStatus('🔴 Opname gestart - spreek nu!');
      document.getElementById('start-recording').textContent = 'Stop Opname';
      
    } catch (error) {
      updateStatus(`❌ Opname setup fout: ${error.message}`);
      window.AppAudio.stopAudioStream(result.stream);
    }
  } else {
    updateStatus(`❌ Microfoon fout: ${result.error}`);
  }
}

/**
 * Initialize UI event handlers
 */
function initializeUI() {
  const startButton = document.getElementById('start-broadcast');
  const listenButton = document.getElementById('join-listener');
  const testMicButton = document.getElementById('test-microphone');
  const startRecButton = document.getElementById('start-recording');
  const disconnectButton = document.getElementById('disconnect');
  
  // Setup initial state
  if (startButton) startButton.disabled = false;
  if (listenButton) listenButton.disabled = false;
  if (disconnectButton) disconnectButton.disabled = true;
  
  // Attach event handlers
  if (startButton) startButton.addEventListener('click', startBroadcast);
  if (listenButton) listenButton.addEventListener('click', joinListener);
  if (testMicButton) testMicButton.addEventListener('click', testMicrophone);
  if (startRecButton) startRecButton.addEventListener('click', startRecording);
  if (disconnectButton) {
    disconnectButton.addEventListener('click', window.AppConnection.disconnectWebSocket);
  }
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { updateStatus, enableButtons, startBroadcast, joinListener, testMicrophone, startRecording, initializeUI };
}

if (typeof window !== 'undefined') {
  window.AppUI = { updateStatus, enableButtons, startBroadcast, joinListener, testMicrophone, startRecording, initializeUI };
}