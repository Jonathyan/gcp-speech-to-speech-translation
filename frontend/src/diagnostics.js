/**
 * Diagnostics Module
 * Browser capability reporting and audio system diagnostics
 */

/**
 * Get browser capabilities report
 * @returns {object} Comprehensive browser capability report
 */
function getBrowserCapabilities() {
  const capabilities = {
    browser: {
      userAgent: navigator.userAgent,
      language: navigator.language,
      platform: navigator.platform,
      cookieEnabled: navigator.cookieEnabled
    },
    audio: {
      getUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
      mediaRecorder: typeof MediaRecorder !== 'undefined',
      webAudio: typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined',
      supportedFormats: []
    },
    network: {
      webSocket: typeof WebSocket !== 'undefined',
      onLine: navigator.onLine,
      connection: navigator.connection ? {
        effectiveType: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
        rtt: navigator.connection.rtt
      } : null
    },
    performance: {
      timing: performance.timing ? {
        loadTime: performance.timing.loadEventEnd - performance.timing.navigationStart,
        domReady: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart
      } : null,
      memory: performance.memory ? {
        usedJSHeapSize: performance.memory.usedJSHeapSize,
        totalJSHeapSize: performance.memory.totalJSHeapSize,
        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
      } : null
    }
  };

  // Test audio format support
  if (typeof MediaRecorder !== 'undefined') {
    const formats = ['audio/webm', 'audio/mp4', 'audio/wav', 'audio/ogg'];
    formats.forEach(format => {
      if (MediaRecorder.isTypeSupported(format)) {
        capabilities.audio.supportedFormats.push(format);
      }
    });
  }

  return capabilities;
}

/**
 * Run audio system diagnostics
 * @returns {Promise<object>} Audio system diagnostic results
 */
async function runAudioDiagnostics() {
  const diagnostics = {
    timestamp: new Date().toISOString(),
    microphoneAccess: null,
    recordingCapability: null,
    formatSupport: null,
    errors: []
  };

  try {
    // Test microphone access
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        diagnostics.microphoneAccess = {
          success: true,
          tracks: stream.getAudioTracks().length,
          constraints: stream.getAudioTracks()[0]?.getSettings() || null
        };
        
        // Test recording capability
        if (typeof MediaRecorder !== 'undefined') {
          try {
            const recorder = new MediaRecorder(stream);
            diagnostics.recordingCapability = {
              success: true,
              state: recorder.state,
              mimeType: recorder.mimeType
            };
          } catch (error) {
            diagnostics.recordingCapability = {
              success: false,
              error: error.message
            };
            diagnostics.errors.push(`Recording test failed: ${error.message}`);
          }
        } else {
          diagnostics.recordingCapability = {
            success: false,
            error: 'MediaRecorder not supported'
          };
        }
        
        // Cleanup
        stream.getTracks().forEach(track => track.stop());
        
      } catch (error) {
        diagnostics.microphoneAccess = {
          success: false,
          error: error.name,
          message: error.message
        };
        diagnostics.errors.push(`Microphone access failed: ${error.message}`);
      }
    } else {
      diagnostics.microphoneAccess = {
        success: false,
        error: 'getUserMedia not supported'
      };
    }

    // Test format support
    diagnostics.formatSupport = getBrowserCapabilities().audio.supportedFormats;

  } catch (error) {
    diagnostics.errors.push(`Diagnostic error: ${error.message}`);
  }

  return diagnostics;
}

/**
 * Generate debug information
 * @returns {object} Debug information for troubleshooting
 */
function generateDebugInfo() {
  const debugInfo = {
    timestamp: new Date().toISOString(),
    capabilities: getBrowserCapabilities(),
    config: window.AppConfig ? {
      environment: window.AppConfig.getEnvironment(),
      audioConstraints: window.AppConfig.getAudioConstraints(),
      chunkConfig: window.AppConfig.getAudioChunkConfig(),
      bestFormat: window.AppConfig.getBestAudioFormat()
    } : null,
    errors: [],
    recommendations: []
  };

  // Generate recommendations based on capabilities
  const caps = debugInfo.capabilities;
  
  if (!caps.audio.getUserMedia) {
    debugInfo.recommendations.push('Upgrade to a modern browser that supports getUserMedia API');
  }
  
  if (!caps.audio.mediaRecorder) {
    debugInfo.recommendations.push('MediaRecorder not supported - audio recording unavailable');
  }
  
  if (caps.audio.supportedFormats.length === 0) {
    debugInfo.recommendations.push('No supported audio formats detected - check browser compatibility');
  }
  
  if (!caps.network.webSocket) {
    debugInfo.recommendations.push('WebSocket not supported - real-time communication unavailable');
  }

  return debugInfo;
}

/**
 * Performance metrics collection
 */
class PerformanceMetrics {
  constructor() {
    this.metrics = {
      audioChunks: {
        total: 0,
        successful: 0,
        failed: 0,
        averageSize: 0,
        totalSize: 0
      },
      webSocket: {
        connects: 0,
        disconnects: 0,
        errors: 0,
        messagesSent: 0,
        messagesFailed: 0
      },
      timing: {
        microphoneAccessTime: 0,
        connectionTime: 0,
        firstChunkTime: 0
      }
    };
  }

  recordAudioChunk(size, success = true) {
    this.metrics.audioChunks.total++;
    if (success) {
      this.metrics.audioChunks.successful++;
      this.metrics.audioChunks.totalSize += size;
      this.metrics.audioChunks.averageSize = 
        this.metrics.audioChunks.totalSize / this.metrics.audioChunks.successful;
    } else {
      this.metrics.audioChunks.failed++;
    }
  }

  recordWebSocketEvent(event, success = true) {
    if (event === 'connect') {
      this.metrics.webSocket.connects++;
    } else if (event === 'disconnect') {
      this.metrics.webSocket.disconnects++;
    } else if (event === 'message') {
      if (success) {
        this.metrics.webSocket.messagesSent++;
      } else {
        this.metrics.webSocket.messagesFailed++;
      }
    } else if (event === 'error') {
      this.metrics.webSocket.errors++;
    }
  }

  recordTiming(event, duration) {
    this.metrics.timing[event] = duration;
  }

  getReport() {
    return {
      timestamp: new Date().toISOString(),
      ...this.metrics,
      successRates: {
        audioChunks: this.metrics.audioChunks.total > 0 ? 
          (this.metrics.audioChunks.successful / this.metrics.audioChunks.total * 100).toFixed(2) + '%' : 'N/A',
        webSocketMessages: this.metrics.webSocket.messagesSent + this.metrics.webSocket.messagesFailed > 0 ?
          (this.metrics.webSocket.messagesSent / (this.metrics.webSocket.messagesSent + this.metrics.webSocket.messagesFailed) * 100).toFixed(2) + '%' : 'N/A'
      }
    };
  }
}

// Global performance metrics instance
const performanceMetrics = new PerformanceMetrics();

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getBrowserCapabilities,
    runAudioDiagnostics,
    generateDebugInfo,
    PerformanceMetrics,
    performanceMetrics
  };
}

if (typeof window !== 'undefined') {
  window.AppDiagnostics = {
    getBrowserCapabilities,
    runAudioDiagnostics,
    generateDebugInfo,
    PerformanceMetrics,
    performanceMetrics
  };
}