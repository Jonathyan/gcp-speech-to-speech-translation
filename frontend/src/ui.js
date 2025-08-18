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
 * Set loading state with visual feedback
 * @param {boolean} loading - Whether to show loading state
 * @param {string} message - Loading message
 */
function setLoadingState(loading, message = '') {
  const statusDiv = document.getElementById('status');
  const startButton = document.getElementById('start-broadcast');
  
  if (loading) {
    if (statusDiv) {
      statusDiv.innerHTML = `<span class="loading-spinner">⏳</span> ${message}`;
      statusDiv.classList.add('loading');
    }
    if (startButton) startButton.disabled = true;
  } else {
    if (statusDiv) {
      statusDiv.classList.remove('loading');
    }
    if (startButton) startButton.disabled = false;
  }
}

/**
 * Show error message with suggestion and recovery options
 * @param {string} error - Error message
 * @param {string} suggestion - Recovery suggestion
 * @param {object} options - Additional error options
 */
function showError(error, suggestion = '', options = {}) {
  const statusDiv = document.getElementById('status');
  if (statusDiv) {
    statusDiv.innerHTML = `❌ ${error}`;
    statusDiv.classList.add('error');
    
    if (suggestion) {
      setTimeout(() => {
        statusDiv.innerHTML += `<br><small>💡 ${suggestion}</small>`;
      }, 1000);
    }
    
    // Add recovery button if error is recoverable
    if (options.recoverable) {
      setTimeout(() => {
        const recoveryBtn = document.createElement('button');
        recoveryBtn.textContent = 'Probeer Opnieuw';
        recoveryBtn.style.cssText = 'margin-left: 10px; padding: 5px 10px; font-size: 12px;';
        recoveryBtn.onclick = () => {
          if (options.onRetry) options.onRetry();
          statusDiv.classList.remove('error');
          updateStatus('Opnieuw proberen...');
        };
        statusDiv.appendChild(recoveryBtn);
      }, 2000);
    }
    
    // Clear error state after specified time or default 10 seconds
    const clearTime = options.clearTime || 10000;
    setTimeout(() => {
      statusDiv.classList.remove('error');
      updateStatus('Ready');
    }, clearTime);
  }
}

/**
 * Show audio loading indicator with progress
 * @param {boolean} loading - Whether audio is loading
 * @param {string} message - Loading message
 * @param {number} progress - Progress percentage (0-100)
 */
function showAudioLoading(loading, message = 'Audio laden...', progress = 0) {
  let indicator = document.getElementById('audio-loading-indicator');
  
  if (loading) {
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'audio-loading-indicator';
      indicator.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        z-index: 10001;
        font-family: Arial, sans-serif;
      `;
      document.body.appendChild(indicator);
    }
    
    indicator.innerHTML = `
      <div style="margin-bottom: 10px;">🎧 ${message}</div>
      <div style="width: 200px; height: 4px; background: #333; border-radius: 2px; overflow: hidden;">
        <div style="width: ${progress}%; height: 100%; background: #007bff; transition: width 0.3s;"></div>
      </div>
      <div style="font-size: 12px; margin-top: 5px;">${progress}%</div>
    `;
  } else {
    if (indicator) {
      indicator.remove();
    }
  }
}

/**
 * Show audio quality indicator
 * @param {string} quality - Quality level (excellent, good, fair, poor)
 * @param {object} metrics - Quality metrics
 */
function showAudioQuality(quality, metrics = {}) {
  let indicator = document.getElementById('audio-quality-indicator');
  
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.id = 'audio-quality-indicator';
    indicator.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      padding: 10px;
      border-radius: 5px;
      font-size: 12px;
      z-index: 1000;
      min-width: 120px;
    `;
    document.body.appendChild(indicator);
  }
  
  const qualityColors = {
    excellent: '#28a745',
    good: '#17a2b8',
    fair: '#ffc107',
    poor: '#dc3545',
    unknown: '#6c757d'
  };
  
  const qualityIcons = {
    excellent: '🟢',
    good: '🔵',
    fair: '🟡',
    poor: '🔴',
    unknown: '⚪'
  };
  
  indicator.style.borderLeft = `4px solid ${qualityColors[quality] || qualityColors.unknown}`;
  
  let content = `${qualityIcons[quality] || qualityIcons.unknown} Audio: ${quality}`;
  
  if (metrics.latency) {
    content += `<br>Latency: ${metrics.latency}`;
  }
  if (metrics.dropRate !== undefined) {
    content += `<br>Drops: ${metrics.dropRate}%`;
  }
  
  indicator.innerHTML = content;
}

/**
 * Show recording indicator with pulsing effect
 * @param {boolean} recording - Whether recording is active
 */
function showRecordingIndicator(recording) {
  let indicator = document.getElementById('recording-indicator');
  
  if (recording) {
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'recording-indicator';
      indicator.innerHTML = '🔴';
      indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        font-size: 24px;
        animation: pulse 1s infinite;
        z-index: 1000;
      `;
      document.body.appendChild(indicator);
      
      // Add CSS animation if not exists
      if (!document.getElementById('recording-styles')) {
        const style = document.createElement('style');
        style.id = 'recording-styles';
        style.textContent = `
          @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.1); }
            100% { opacity: 1; transform: scale(1); }
          }
          .loading { color: #007bff; }
          .error { color: #dc3545; }
        `;
        document.head.appendChild(style);
      }
    }
  } else {
    if (indicator) {
      indicator.remove();
    }
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
  
  // Don't disable buttons if we're in an active session
  if (!isBroadcasting && !isListening) {
    if (startButton) startButton.disabled = !enabled;
    if (listenButton) listenButton.disabled = !enabled;
  }
  
  if (disconnectButton) disconnectButton.disabled = enabled;
}

/**
 * Handle start broadcast button click
 */
async function startBroadcast() {
  if (isBroadcasting) {
    stopBroadcast();
    return;
  }
  
  // Add loading state
  setLoadingState(true, 'Microfoon toegang aanvragen...');
  
  // Request microphone access with retry
  const micResult = await window.AppAudio.requestMicrophoneAccess(2);
  if (!micResult.success) {
    setLoadingState(false);
    showError(micResult.error, micResult.suggestion);
    return;
  }
  
  broadcastStream = micResult.stream;
  // Get stream ID from input field or generate new one
  const streamIdInput = document.getElementById('stream-id');
  currentStreamId = streamIdInput ? streamIdInput.value.trim() || window.AppConnection.generateStreamId() : window.AppConnection.generateStreamId();
  
  // Setup WebSocket connection - fallback to broadcast mode while debugging streaming
  updateStatus('Verbinden...');
  const url = window.AppConfig.getWebSocketURL();
  window.AppConnection.connectWebSocket(url, 'streaming', currentStreamId);
  
  // Wait longer for connection to be established
  setTimeout(async () => {
    const websocket = window.AppConnection.getCurrentWebSocket();
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      // Give it more time if still connecting
      if (websocket && websocket.readyState === WebSocket.CONNECTING) {
        setTimeout(async () => {
          const ws = window.AppConnection.getCurrentWebSocket();
          if (!ws || ws.readyState !== WebSocket.OPEN) {
            updateStatus('❌ Verbinding mislukt');
            window.AppAudio.stopAudioStream(broadcastStream);
            return;
          }
          startRecordingAfterConnection(ws, broadcastStream, currentStreamId);
        }, 2000); // Wait 2 more seconds
        return;
      }
      updateStatus('❌ Verbinding mislukt');
      window.AppAudio.stopAudioStream(broadcastStream);
      return;
    }
    
    // Connection successful, start recording
    startRecordingAfterConnection(websocket, broadcastStream, currentStreamId);
  }, 1000);
}

/**
 * Start recording after connection is established
 */
function startRecordingAfterConnection(websocket, stream, streamId) {
  try {
    // Start audio recording
    broadcastRecorder = new window.AppAudio.AudioRecorder(stream, {
      onDataAvailable: async (data) => {
        try {
          console.log(`🎧 UI received audio data:`, data);
          const arrayBuffer = await window.AppAudio.convertAudioChunk(data);
          console.log(`🔄 Converted to ArrayBuffer:`, arrayBuffer.byteLength, 'bytes');
          const validation = window.AppAudio.validateAudioChunk(arrayBuffer);
          console.log(`✅ Validation result:`, validation);
          
          if (validation.isValid) {
            console.log(`📡 Sending ${arrayBuffer.byteLength} bytes via WebSocket...`);
            const sendResult = window.AppConnection.sendAudioChunk(websocket, arrayBuffer);
            console.log(`📤 WebSocket send result:`, sendResult);
            if (sendResult.success) {
              updateStatus(`🔴 Uitzending actief - Stream ID: ${streamId} - ${validation.size} bytes verzonden`);
            } else {
              console.warn('Failed to send audio:', sendResult.error);
            }
          } else {
            console.warn('⚠️ Audio validation failed:', validation);
          }
        } catch (error) {
          console.error('Audio processing error:', error);
        }
      },
      onError: (error) => {
        console.error('Recording error:', error);
        stopBroadcast();
      }
    });
    
    broadcastRecorder.start();
    isBroadcasting = true;
    
    // Update UI with recording indicator
    setLoadingState(false);
    updateStatus(`🔴 Uitzending actief - Stream ID: ${streamId}`);
    document.getElementById('start-broadcast').textContent = 'Stop Uitzending';
    document.getElementById('disconnect').disabled = false;
  } catch (error) {
    console.error('Recording setup error:', error);
    updateStatus(`❌ Opname setup fout: ${error.message}`);
    window.AppAudio.stopAudioStream(stream);
  }
}

/**
 * Stop broadcast function
 */
function stopBroadcast() {
  if (broadcastRecorder) {
    broadcastRecorder.stop();
    broadcastRecorder = null;
  }
  
  if (broadcastStream) {
    window.AppAudio.stopAudioStream(broadcastStream);
    broadcastStream = null;
  }
  
  window.AppConnection.disconnectWebSocket();
  
  isBroadcasting = false;
  currentStreamId = null;
  
  // Update UI
  showRecordingIndicator(false);
  updateStatus('Uitzending gestopt');
  const startButton = document.getElementById('start-broadcast');
  if (startButton) startButton.textContent = 'Start Uitzending';
}

/**
 * Handle join listener button click
 */
function joinListener() {
  if (isListening) {
    stopListening();
    return;
  }
  
  setLoadingState(true, 'Audio systeem initialiseren...');
  
  // Check Web Audio API support
  if (!window.AppUtils.isWebAudioSupported()) {
    setLoadingState(false);
    showError('Web Audio API niet ondersteund', 'Upgrade naar een moderne browser');
    return;
  }
  
  // Get stream ID from input field
  const streamIdInput = document.getElementById('stream-id');
  currentStreamId = streamIdInput ? streamIdInput.value.trim() || 'test-stream' : 'test-stream';
  
  try {
    // Initialize AudioPlayer and connect
    updateStatus('Verbinden als luisteraar...');
    const url = window.AppConfig.getWebSocketURL();
    window.AppConnection.connectWebSocket(url, 'listener', currentStreamId);
    
    // Wait for connection and start listening
    setTimeout(() => {
      const websocket = window.AppConnection.getCurrentWebSocket();
      if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        setLoadingState(false);
        showError('Verbinding mislukt', 'Controleer of de server draait');
        return;
      }
      
      isListening = true;
      setLoadingState(false);
      updateListenerUI();
      startAudioStatusMonitoring();
      
    }, 1000);
    
  } catch (error) {
    setLoadingState(false);
    showError('Luisteraar setup fout', error.message);
  }
}

/**
 * Stop listening function
 */
function stopListening() {
  window.AppConnection.disconnectWebSocket();
  
  isListening = false;
  currentStreamId = null;
  
  stopAudioStatusMonitoring();
  updateListenerUI();
  updateStatus('Luisteren gestopt');
}

/**
 * Update UI for listener mode
 */
function updateListenerUI() {
  const listenButton = document.getElementById('join-listener');
  const startButton = document.getElementById('start-broadcast');
  const disconnectButton = document.getElementById('disconnect');
  
  if (isListening) {
    if (listenButton) listenButton.textContent = 'Stop Luisteren';
    if (startButton) startButton.disabled = true;
    if (disconnectButton) disconnectButton.disabled = false;
    showListeningIndicator(true);
  } else {
    if (listenButton) listenButton.textContent = 'Luisteren';
    if (startButton) startButton.disabled = false;
    if (disconnectButton) disconnectButton.disabled = true;
    showListeningIndicator(false);
  }
}

/**
 * Show listening indicator
 * @param {boolean} listening - Whether listening is active
 */
function showListeningIndicator(listening) {
  let indicator = document.getElementById('listening-indicator');
  
  if (listening) {
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'listening-indicator';
      indicator.innerHTML = '🎧';
      indicator.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        font-size: 24px;
        animation: pulse 2s infinite;
        z-index: 1000;
      `;
      document.body.appendChild(indicator);
    }
  } else {
    if (indicator) {
      indicator.remove();
    }
  }
}

/**
 * Start enhanced audio status monitoring with quality metrics
 */
function startEnhancedAudioMonitoring() {
  if (audioStatusInterval) {
    clearInterval(audioStatusInterval);
  }
  
  audioStatusInterval = setInterval(() => {
    if (!isListening) {
      clearInterval(audioStatusInterval);
      return;
    }
    
    const stats = window.AppConnection.getAudioStats();
    const playerStatus = getAudioPlayerStatus();
    
    // Update status with comprehensive info
    let statusParts = [`🎧 Luisteren - Stream: ${currentStreamId}`];
    
    if (stats.chunksReceived > 0) {
      statusParts.push(`Ontvangen: ${stats.chunksReceived} chunks (${Math.round(stats.bytesReceived/1024)}KB)`);
    }
    
    if (stats.processingErrors > 0) {
      statusParts.push(`Fouten: ${stats.processingErrors}`);
    }
    
    if (playerStatus.isStreaming) {
      statusParts.push(`Afspelen: ${playerStatus.queueSize} in wachtrij`);
      statusParts.push(`Kwaliteit: ${playerStatus.quality}`);
    }
    
    updateStatus(statusParts.join(' | '));
    
    // Update quality indicator
    if (playerStatus.quality !== 'Unknown') {
      const metrics = playerStatus.metrics;
      showAudioQuality(playerStatus.quality.toLowerCase(), {
        latency: metrics.avgLatency ? `${Math.round(metrics.avgLatency)}ms` : 'N/A',
        dropRate: metrics.droppedChunks && metrics.processedChunks ? 
          Math.round((metrics.droppedChunks / (metrics.processedChunks + metrics.droppedChunks)) * 100) : 0
      });
    }
    
    // Show audio level if available
    if (stats.audioLevel !== undefined) {
      showAudioLevel(stats.audioLevel);
    }
    
  }, 1000); // More frequent updates for better UX
}

/**
 * Start audio status monitoring (legacy - use startEnhancedAudioMonitoring)
 */
function startAudioStatusMonitoring() {
  startEnhancedAudioMonitoring();
}

/**
 * Stop audio status monitoring
 */
function stopAudioStatusMonitoring() {
  if (audioStatusInterval) {
    clearInterval(audioStatusInterval);
    audioStatusInterval = null;
  }
}

/**
 * Show audio level visualization
 * @param {number} level - Audio level (0-100)
 */
function showAudioLevel(level) {
  let indicator = document.getElementById('audio-level-indicator');
  
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.id = 'audio-level-indicator';
    indicator.style.cssText = `
      position: fixed;
      bottom: 20px;
      left: 20px;
      width: 20px;
      height: 100px;
      background: rgba(0, 0, 0, 0.7);
      border-radius: 10px;
      z-index: 1000;
      overflow: hidden;
    `;
    document.body.appendChild(indicator);
  }
  
  const levelHeight = Math.max(2, (level / 100) * 100);
  const levelColor = level > 80 ? '#dc3545' : level > 60 ? '#ffc107' : '#28a745';
  
  indicator.innerHTML = `
    <div style="
      position: absolute;
      bottom: 0;
      width: 100%;
      height: ${levelHeight}%;
      background: ${levelColor};
      transition: height 0.1s, background-color 0.3s;
    "></div>
  `;
}

/**
 * Hide audio level visualization
 */
function hideAudioLevel() {
  const indicator = document.getElementById('audio-level-indicator');
  if (indicator) {
    indicator.remove();
  }
}

/**
 * Show comprehensive error dialog with diagnostics
 * @param {object} errorInfo - Detailed error information
 */
function showErrorDialog(errorInfo) {
  // Remove existing dialog
  const existing = document.getElementById('error-dialog');
  if (existing) existing.remove();
  
  const dialog = document.createElement('div');
  dialog.id = 'error-dialog';
  dialog.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10002;
    font-family: Arial, sans-serif;
  `;
  
  dialog.innerHTML = `
    <div style="
      background: white;
      padding: 30px;
      border-radius: 10px;
      max-width: 500px;
      max-height: 80vh;
      overflow-y: auto;
    ">
      <h3 style="color: #dc3545; margin-top: 0;">🚨 Audio Systeem Fout</h3>
      <p><strong>Fout:</strong> ${errorInfo.error}</p>
      <p><strong>Oorzaak:</strong> ${errorInfo.operation}</p>
      <p><strong>Suggestie:</strong> ${errorInfo.suggestion}</p>
      
      ${errorInfo.diagnostics ? `
        <details style="margin: 15px 0;">
          <summary style="cursor: pointer; font-weight: bold;">🔧 Diagnostische Informatie</summary>
          <pre style="background: #f8f9fa; padding: 10px; border-radius: 5px; font-size: 12px; overflow-x: auto;">${JSON.stringify(errorInfo.diagnostics, null, 2)}</pre>
        </details>
      ` : ''}
      
      <div style="text-align: right; margin-top: 20px;">
        ${errorInfo.recoverable ? `
          <button onclick="handleErrorRecovery('${errorInfo.operation}')" style="
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-right: 10px;
          ">Probeer Opnieuw</button>
        ` : ''}
        <button onclick="closeErrorDialog()" style="
          background: #6c757d;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 5px;
          cursor: pointer;
        ">Sluiten</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(dialog);
}

/**
 * Close error dialog
 */
function closeErrorDialog() {
  const dialog = document.getElementById('error-dialog');
  if (dialog) dialog.remove();
}

/**
 * Handle error recovery based on operation type
 * @param {string} operation - Operation that failed
 */
function handleErrorRecovery(operation) {
  closeErrorDialog();
  
  switch (operation) {
    case 'decode':
      updateStatus('Audio decodering herstarten...');
      // Restart audio processing
      if (isListening) {
        stopListening();
        setTimeout(() => joinListener(), 1000);
      }
      break;
    case 'playback':
      updateStatus('Audio afspelen herstarten...');
      // Restart playback system
      if (window.AppConnection.audioPlayer) {
        window.AppConnection.audioPlayer.stopStreamPlayback();
        setTimeout(() => {
          window.AppConnection.audioPlayer.startStreamPlayback();
        }, 500);
      }
      break;
    case 'context':
      updateStatus('Audio systeem herstarten...');
      // Full audio system restart
      location.reload();
      break;
    default:
      updateStatus('Systeem herstarten...');
      location.reload();
  }
}

/**
 * Get comprehensive audio player status
 * @returns {object} Audio player status information
 */
function getAudioPlayerStatus() {
  if (window.AppConnection && window.AppConnection.audioPlayer) {
    const player = window.AppConnection.audioPlayer;
    const health = player.getHealthReport ? player.getHealthReport() : {};
    const quality = player.getPlaybackQuality ? player.getPlaybackQuality() : {};
    
    return {
      isStreaming: player.isStreaming || false,
      queueSize: player.getQueueSize ? player.getQueueSize() : 0,
      isPlaying: player.isPlaying || false,
      health: health.overall || 'Unknown',
      quality: quality.overall || 'Unknown',
      metrics: player.getPerformanceMetrics ? player.getPerformanceMetrics() : {}
    };
  }
  
  return {
    isStreaming: false,
    queueSize: 0,
    isPlaying: false,
    health: 'Not initialized',
    quality: 'Unknown',
    metrics: {}
  };
}

/**
 * Setup audio player error handling
 */
function setupAudioErrorHandling() {
  if (window.AppConnection && window.AppConnection.audioPlayer) {
    const player = window.AppConnection.audioPlayer;
    
    // Setup error callback
    player.onError = (errorInfo) => {
      console.error('Audio Player Error:', errorInfo);
      
      // Show user-friendly error with recovery options
      showError(errorInfo.error, errorInfo.suggestion, {
        recoverable: errorInfo.recoverable,
        onRetry: () => handleErrorRecovery(errorInfo.operation),
        clearTime: 15000
      });
      
      // Show detailed error dialog for critical errors
      if (errorInfo.operation === 'context' || !errorInfo.recoverable) {
        const diagnostics = player.getHealthReport ? player.getHealthReport() : null;
        showErrorDialog({
          ...errorInfo,
          diagnostics
        });
      }
    };
    
    // Setup recovery callback
    player.onRecovery = (recoveryInfo) => {
      console.log('Audio Player Recovery:', recoveryInfo);
      updateStatus(`✅ ${recoveryInfo.message}`);
    };
    
    // Setup quality change callback
    player.onQualityChange = (quality) => {
      const metrics = player.getPlaybackQuality();
      showAudioQuality(quality, {
        latency: metrics.latency,
        dropRate: metrics.stability === 'Poor' ? '> 10' : '< 5'
      });
    };
  }
}

// Global recording state
let currentRecorder = null;
let recordingStream = null;
let broadcastRecorder = null;
let broadcastStream = null;
let currentStreamId = null;
let isBroadcasting = false;

// Global listening state
let isListening = false;
let audioStatusInterval = null;

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
              
              // Send audio chunk via WebSocket if connected
              const websocket = window.AppConnection.getCurrentWebSocket();
              if (websocket) {
                const sendResult = window.AppConnection.sendAudioChunk(websocket, arrayBuffer);
                if (!sendResult.success) {
                  console.warn('Failed to send audio chunk:', sendResult.error);
                }
              }
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
 * Run diagnostics and display results
 */
async function runDiagnostics() {
  setLoadingState(true, 'Diagnostiek uitvoeren...');
  
  try {
    const diagnostics = await window.AppDiagnostics.runAudioDiagnostics();
    const capabilities = window.AppDiagnostics.getBrowserCapabilities();
    const debugInfo = window.AppDiagnostics.generateDebugInfo();
    
    setLoadingState(false);
    
    // Display results in console and status
    console.group('🔧 Diagnostiek Resultaten');
    console.log('Audio Diagnostiek:', diagnostics);
    console.log('Browser Mogelijkheden:', capabilities);
    console.log('Debug Informatie:', debugInfo);
    console.groupEnd();
    
    // Show summary in status
    const micStatus = diagnostics.microphoneAccess?.success ? '✅' : '❌';
    const recStatus = diagnostics.recordingCapability?.success ? '✅' : '❌';
    const formatCount = diagnostics.formatSupport?.length || 0;
    
    updateStatus(`Diagnostiek: Microfoon ${micStatus} | Opname ${recStatus} | Formaten: ${formatCount}`);
    
    if (debugInfo.recommendations.length > 0) {
      setTimeout(() => {
        showError('Aanbevelingen beschikbaar', 'Bekijk de console voor details');
      }, 2000);
    }
    
  } catch (error) {
    setLoadingState(false);
    showError('Diagnostiek mislukt', error.message);
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
  const diagnosticsButton = document.getElementById('run-diagnostics');
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
  if (diagnosticsButton) diagnosticsButton.addEventListener('click', runDiagnostics);
  if (disconnectButton) {
    disconnectButton.addEventListener('click', window.AppConnection.disconnectWebSocket);
  }
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { 
    updateStatus, 
    enableButtons, 
    startBroadcast, 
    stopBroadcast, 
    joinListener, 
    stopListening,
    testMicrophone, 
    startRecording, 
    initializeUI, 
    setLoadingState, 
    showError, 
    showRecordingIndicator,
    showListeningIndicator,
    updateListenerUI
  };
}

if (typeof window !== 'undefined') {
  window.AppUI = { 
    updateStatus, 
    enableButtons, 
    startBroadcast, 
    stopBroadcast, 
    joinListener, 
    stopListening,
    testMicrophone, 
    startRecording, 
    initializeUI, 
    setLoadingState, 
    showError, 
    showRecordingIndicator,
    showListeningIndicator,
    updateListenerUI
  };
}