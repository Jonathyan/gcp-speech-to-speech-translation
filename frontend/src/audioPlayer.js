/**
 * AudioPlayer Module
 * Handles Web Audio API for audio playback
 */

class AudioPlayer {
  constructor() {
    this.audioContext = null;
    this.isSupported = AudioPlayer.isSupported();
    this.audioQueue = [];
    this.maxQueueSize = 50; // Maximum number of audio buffers
    this.isPlaying = false;
    this.currentPlaybackTime = 0;
    this.onPlaybackComplete = null;
    this.isStreaming = false;
    this.nextPlaybackTime = 0;
    this.activeSources = [];
    
    // Performance optimization properties
    this.bufferPool = [];
    this.maxPoolSize = 20;
    this.performanceMetrics = {
      decodeTime: [],
      queueSize: [],
      memoryUsage: [],
      latency: [],
      processedChunks: 0,
      droppedChunks: 0
    };
    this.lastProcessTime = 0;
    this.maxDecodeTime = 100; // ms
    this.maxQueueMemory = 50 * 1024 * 1024; // 50MB
    
    // Error recovery properties
    this.consecutiveFailures = 0;
    this.recoveryMode = false;
    this.recoveryStartTime = 0;
    this.userGestureRequested = false;
    this.errorHistory = [];
    
    // User feedback properties
    this.onError = null; // Callback for error notifications
    this.onRecovery = null; // Callback for recovery notifications
    this.onQualityChange = null; // Callback for quality changes
  }

  /**
   * Check if Web Audio API is supported
   * @returns {boolean} True if supported
   */
  static isSupported() {
    return typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined';
  }

  /**
   * Create and initialize AudioContext
   * @returns {AudioContext|null} AudioContext instance or null if failed
   */
  createAudioContext() {
    if (!this.isSupported) {
      throw new Error('Web Audio API not supported');
    }

    try {
      // Try AudioContext, fallback to webkitAudioContext
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContextClass();
      
      // Handle suspended state (Chrome autoplay policy)
      if (this.audioContext.state === 'suspended') {
        // Will be resumed on user gesture
        console.log('AudioContext suspended - will resume on user interaction');
      }
      
      return this.audioContext;
    } catch (error) {
      console.error('Failed to create AudioContext:', error);
      throw new Error(`AudioContext creation failed: ${error.message}`);
    }
  }

  /**
   * Decode audio chunk from ArrayBuffer with comprehensive error recovery
   * @param {ArrayBuffer} arrayBuffer - Audio data to decode
   * @returns {Promise<AudioBuffer>} Decoded audio buffer
   */
  async decodeAudioChunk(arrayBuffer) {
    if (!this.audioContext) {
      const error = new Error('AudioContext not initialized');
      this._logError(error, 'decode');
      this._notifyError('context', error);
      throw this._createUserFriendlyError('context', error);
    }

    if (!arrayBuffer || arrayBuffer.byteLength === 0) {
      this.performanceMetrics.droppedChunks++;
      const error = new Error('Invalid audio data');
      this._logError(error, 'decode');
      throw this._createUserFriendlyError('decode', error);
    }

    const startTime = performance.now();
    let retryCount = 0;
    const maxRetries = this.recoveryMode ? 1 : 3; // Fewer retries in recovery mode
    let lastError;
    
    while (retryCount <= maxRetries) {
      try {
        // Check memory pressure before decoding
        if (this._isMemoryPressure()) {
          this._performEmergencyCleanup();
          if (this.audioQueue.length > this.maxQueueSize / 2) {
            this.performanceMetrics.droppedChunks++;
            const error = new Error('Memory pressure - dropping chunk');
            this._logError(error, 'decode');
            throw this._createUserFriendlyError('decode', error);
          }
        }
        
        // Handle AudioContext suspension with automatic recovery
        if (this.audioContext.state === 'suspended') {
          try {
            await this._resumeAudioContextWithUserGesture();
          } catch (resumeError) {
            this._logError(resumeError, 'context');
            this._notifyError('context', resumeError);
            throw this._createUserFriendlyError('context', resumeError);
          }
        }
        
        // Add timeout protection with progressive timeouts
        const timeoutMs = Math.min(5000 + (retryCount * 2000), 15000);
        const decodePromise = this.audioContext.decodeAudioData(arrayBuffer.slice());
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Audio decoding timeout')), timeoutMs)
        );
        
        const audioBuffer = await Promise.race([decodePromise, timeoutPromise]);
        
        // Validate decoded audio
        if (!this._isValidDecodedAudio(audioBuffer)) {
          throw new Error('Decoded audio validation failed');
        }
        
        // Record performance metrics
        const decodeTime = performance.now() - startTime;
        this._recordDecodeTime(decodeTime);
        this.performanceMetrics.processedChunks++;
        
        // Reset consecutive failures on success
        if (this.consecutiveFailures > 0) {
          const failureCount = this.consecutiveFailures;
          this.consecutiveFailures = 0;
          this._notifyRecovery('decode', failureCount);
        }
        
        return audioBuffer;
      } catch (error) {
        lastError = error;
        retryCount++;
        this.consecutiveFailures = (this.consecutiveFailures || 0) + 1;
        
        // Log error for diagnostics
        this._logError(error, 'decode');
        
        if (retryCount > maxRetries) {
          this.performanceMetrics.droppedChunks++;
          
          // Trigger recovery mode if too many consecutive failures
          if (this.consecutiveFailures > 10 && !this.recoveryMode) {
            this._enterRecoveryMode();
          }
          
          const userFriendlyError = this._createUserFriendlyError('decode', error);
          // Notify with user-friendly error but preserve original error context
          const notifyError = { ...error };
          notifyError.message = userFriendlyError.message;
          this._notifyError('decode', notifyError);
          throw userFriendlyError;
        }
        
        // Exponential backoff with jitter and adaptive delay
        const baseDelay = Math.pow(2, retryCount) * 100;
        const jitter = Math.random() * 50;
        const adaptiveDelay = this.consecutiveFailures > 5 ? baseDelay * 2 : baseDelay;
        await new Promise(resolve => setTimeout(resolve, adaptiveDelay + jitter));
      }
    }
  }

  /**
   * Validate decoded audio buffer
   * @param {AudioBuffer} audioBuffer - Audio buffer to validate
   * @returns {object} Validation result
   */
  validateAudioBuffer(audioBuffer) {
    const result = {
      valid: false,
      errors: []
    };

    if (!audioBuffer) {
      result.errors.push('AudioBuffer is null or undefined');
      return result;
    }

    if (audioBuffer.sampleRate <= 0) {
      result.errors.push('Invalid sample rate');
    }

    if (audioBuffer.numberOfChannels <= 0) {
      result.errors.push('Invalid number of channels');
    }

    if (audioBuffer.duration <= 0) {
      result.errors.push('Invalid duration');
    }

    result.valid = result.errors.length === 0;
    return result;
  }

  /**
   * Add audio buffer to queue with memory management
   * @param {AudioBuffer} audioBuffer - Audio buffer to add
   * @returns {boolean} True if added successfully
   */
  addToQueue(audioBuffer) {
    if (!audioBuffer) {
      return false;
    }

    // Check memory usage before adding
    const bufferMemory = this._estimateBufferMemory(audioBuffer);
    const currentMemory = this._getCurrentQueueMemory();
    
    if (currentMemory + bufferMemory > this.maxQueueMemory) {
      // Remove oldest buffers to make space
      while (this.audioQueue.length > 0 && 
             this._getCurrentQueueMemory() + bufferMemory > this.maxQueueMemory) {
        const removed = this.audioQueue.shift();
        this._returnBufferToPool(removed);
      }
    }

    // Remove oldest if queue is still full
    if (this.audioQueue.length >= this.maxQueueSize) {
      const removed = this.audioQueue.shift();
      this._returnBufferToPool(removed);
    }

    this.audioQueue.push(audioBuffer);
    this._recordQueueSize(this.audioQueue.length);
    return true;
  }

  /**
   * Get next audio buffer from queue
   * @returns {AudioBuffer|null} Next audio buffer or null if empty
   */
  getNextFromQueue() {
    return this.audioQueue.shift() || null;
  }

  /**
   * Clear all audio buffers from queue with cleanup
   */
  clearQueue() {
    // Return buffers to pool before clearing
    while (this.audioQueue.length > 0) {
      const buffer = this.audioQueue.shift();
      this._returnBufferToPool(buffer);
    }
  }

  /**
   * Get current queue size
   * @returns {number} Number of audio buffers in queue
   */
  getQueueSize() {
    return this.audioQueue.length;
  }

  /**
   * Get total duration of audio in queue
   * @returns {number} Total duration in seconds
   */
  getQueueDuration() {
    return this.audioQueue.reduce((total, buffer) => total + buffer.duration, 0);
  }

  /**
   * Check if system is under memory pressure
   * @returns {boolean} True if memory pressure detected
   * @private
   */
  _isMemoryPressure() {
    // Check if performance.memory is available (Chrome)
    if (typeof performance.memory !== 'undefined') {
      const memInfo = performance.memory;
      const usedRatio = memInfo.usedJSHeapSize / memInfo.jsHeapSizeLimit;
      return usedRatio > 0.8; // 80% memory usage threshold
    }
    
    // Fallback: check queue size and active sources
    return this.audioQueue.length > this.maxQueueSize * 0.9 || 
           this.activeSources.length > 10;
  }

  /**
   * Estimate memory usage of audio buffer
   * @param {AudioBuffer} buffer - Audio buffer to estimate
   * @returns {number} Estimated memory in bytes
   * @private
   */
  _estimateBufferMemory(buffer) {
    if (!buffer) return 0;
    // Estimate: sampleRate * numberOfChannels * duration * 4 bytes per sample
    return buffer.sampleRate * buffer.numberOfChannels * buffer.duration * 4;
  }

  /**
   * Get current queue memory usage
   * @returns {number} Memory usage in bytes
   * @private
   */
  _getCurrentQueueMemory() {
    return this.audioQueue.reduce((total, buffer) => 
      total + this._estimateBufferMemory(buffer), 0);
  }

  /**
   * Clean up buffer pool to free memory
   * @private
   */
  _cleanupBufferPool() {
    // Remove half of the pooled buffers
    const removeCount = Math.floor(this.bufferPool.length / 2);
    this.bufferPool.splice(0, removeCount);
  }

  /**
   * Perform emergency cleanup when system is under severe stress
   * @private
   */
  _performEmergencyCleanup() {
    console.warn('AudioPlayer: Performing emergency cleanup due to memory pressure');
    
    // Clear most of the queue, keeping only recent items
    const keepCount = Math.min(5, this.audioQueue.length);
    const removed = this.audioQueue.splice(0, this.audioQueue.length - keepCount);
    removed.forEach(buffer => this._returnBufferToPool(buffer));
    
    // Clear buffer pool completely
    this.bufferPool = [];
    
    // Stop any active sources that might be consuming memory
    this.activeSources.forEach(source => {
      try {
        source.stop();
      } catch (e) { /* ignore */ }
    });
    this.activeSources = [];
    
    // Force garbage collection if available
    if (typeof window !== 'undefined' && window.gc) {
      window.gc();
    }
  }

  /**
   * Enter recovery mode when system is failing consistently
   * @private
   */
  _enterRecoveryMode() {
    console.warn('AudioPlayer: Entering recovery mode due to consecutive failures');
    
    this.recoveryMode = true;
    this.recoveryStartTime = Date.now();
    
    // Perform aggressive cleanup
    this._performEmergencyCleanup();
    
    // Reduce quality settings temporarily
    this.maxQueueSize = Math.max(10, this.maxQueueSize / 2);
    this.maxDecodeTime = this.maxDecodeTime * 2;
    
    // Schedule recovery mode exit
    setTimeout(() => {
      this._exitRecoveryMode();
    }, 30000); // 30 seconds
  }

  /**
   * Exit recovery mode and restore normal operation
   * @private
   */
  _exitRecoveryMode() {
    if (!this.recoveryMode) return;
    
    console.log('AudioPlayer: Exiting recovery mode');
    
    this.recoveryMode = false;
    this.consecutiveFailures = 0;
    
    // Restore normal settings
    this.maxQueueSize = 50;
    this.maxDecodeTime = 100;
  }

  /**
   * Return buffer to pool for reuse
   * @param {AudioBuffer} buffer - Buffer to return to pool
   * @private
   */
  _returnBufferToPool(buffer) {
    if (this.bufferPool.length < this.maxPoolSize && buffer) {
      this.bufferPool.push(buffer);
    }
  }

  /**
   * Record decode time for performance monitoring
   * @param {number} time - Decode time in milliseconds
   * @private
   */
  _recordDecodeTime(time) {
    this.performanceMetrics.decodeTime.push(time);
    if (this.performanceMetrics.decodeTime.length > 100) {
      this.performanceMetrics.decodeTime.shift();
    }
  }

  /**
   * Record queue size for performance monitoring
   * @param {number} size - Current queue size
   * @private
   */
  _recordQueueSize(size) {
    this.performanceMetrics.queueSize.push(size);
    if (this.performanceMetrics.queueSize.length > 100) {
      this.performanceMetrics.queueSize.shift();
    }
  }

  /**
   * Record latency for performance monitoring
   * @param {number} currentTime - Current timestamp
   * @private
   */
  _recordLatency(currentTime) {
    if (this.lastProcessTime > 0) {
      const latency = currentTime - this.lastProcessTime;
      this.performanceMetrics.latency.push(latency);
      if (this.performanceMetrics.latency.length > 100) {
        this.performanceMetrics.latency.shift();
      }
    }
  }

  /**
   * Get performance metrics
   * @returns {object} Performance metrics data
   */
  getPerformanceMetrics() {
    const metrics = { ...this.performanceMetrics };
    
    // Calculate averages
    if (metrics.decodeTime.length > 0) {
      metrics.avgDecodeTime = metrics.decodeTime.reduce((a, b) => a + b, 0) / metrics.decodeTime.length;
      metrics.maxDecodeTime = Math.max(...metrics.decodeTime);
    }
    
    if (metrics.queueSize.length > 0) {
      metrics.avgQueueSize = metrics.queueSize.reduce((a, b) => a + b, 0) / metrics.queueSize.length;
      metrics.maxQueueSize = Math.max(...metrics.queueSize);
    }
    
    if (metrics.latency.length > 0) {
      metrics.avgLatency = metrics.latency.reduce((a, b) => a + b, 0) / metrics.latency.length;
      metrics.maxLatency = Math.max(...metrics.latency);
    }
    
    // Add current memory info if available
    if (typeof performance.memory !== 'undefined') {
      metrics.memoryInfo = {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      };
    }
    
    metrics.currentQueueMemory = this._getCurrentQueueMemory();
    metrics.bufferPoolSize = this.bufferPool.length;
    
    return metrics;
  }

  /**
   * Reset performance metrics
   */
  resetPerformanceMetrics() {
    this.performanceMetrics = {
      decodeTime: [],
      queueSize: [],
      memoryUsage: [],
      latency: [],
      processedChunks: 0,
      droppedChunks: 0
    };
  }

  /**
   * Resume AudioContext with error handling
   * @private
   */
  async _resumeAudioContext() {
    if (this.audioContext.state === 'suspended') {
      try {
        await this.audioContext.resume();
      } catch (error) {
        throw new Error(`Failed to resume AudioContext: ${error.message}`);
      }
    }
  }

  /**
   * Resume AudioContext with user gesture requirement handling
   * @private
   */
  async _resumeAudioContextWithUserGesture() {
    if (this.audioContext.state === 'suspended') {
      try {
        await this.audioContext.resume();
        
        // If still suspended, it likely needs a user gesture
        if (this.audioContext.state === 'suspended') {
          this._requestUserGesture();
          const gestureError = new Error('AudioContext requires user interaction to resume');
          gestureError.name = 'NotAllowedError';
          throw gestureError;
        }
      } catch (error) {
        if (error.message.includes('user interaction')) {
          this._requestUserGesture();
        }
        throw new Error(`Failed to resume AudioContext: ${error.message}`);
      }
    }
  }

  /**
   * Request user gesture to resume AudioContext
   * @private
   */
  _requestUserGesture() {
    if (this.userGestureRequested) return;
    
    this.userGestureRequested = true;
    
    // Create a temporary overlay to request user interaction
    const overlay = document.createElement('div');
    overlay.id = 'audio-gesture-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.8);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      font-family: Arial, sans-serif;
      text-align: center;
    `;
    
    overlay.innerHTML = `
      <div>
        <h2>🎧 Audio Activatie Vereist</h2>
        <p>Klik hier om audio afspelen te activeren</p>
        <button style="padding: 10px 20px; font-size: 16px; cursor: pointer;">Activeer Audio</button>
      </div>
    `;
    
    const handleClick = async () => {
      try {
        await this.audioContext.resume();
        overlay.remove();
        this.userGestureRequested = false;
        console.log('AudioContext resumed after user gesture');
      } catch (error) {
        console.error('Failed to resume AudioContext after user gesture:', error);
      }
    };
    
    overlay.addEventListener('click', handleClick);
    document.body.appendChild(overlay);
    
    // Auto-remove after 30 seconds
    setTimeout(() => {
      if (overlay.parentNode) {
        overlay.remove();
        this.userGestureRequested = false;
      }
    }, 30000);
  }

  /**
   * Create user-friendly error messages with recovery suggestions
   * @param {string} operation - The operation that failed
   * @param {Error} error - Original error
   * @returns {Error} User-friendly error with recovery info
   * @private
   */
  _createUserFriendlyError(operation, error) {
    const friendlyMessages = {
      decode: {
        'EncodingError': 'Audio bestand is beschadigd of niet ondersteund',
        'DataError': 'Audio data is ongeldig',
        'NotSupportedError': 'Audio formaat wordt niet ondersteund',
        'NetworkError': 'Netwerkfout tijdens audio verwerking',
        'TimeoutError': 'Audio verwerking duurde te lang',
        'default': 'Kan audio niet decoderen'
      },
      playback: {
        'InvalidStateError': 'Audio afspelen is niet mogelijk op dit moment',
        'NotAllowedError': 'Audio afspelen werd geblokkeerd door browser',
        'NotSupportedError': 'Audio afspelen wordt niet ondersteund',
        'NetworkError': 'Verbinding verloren tijdens afspelen',
        'default': 'Kan audio niet afspelen'
      },
      context: {
        'NotAllowedError': 'Audio systeem geblokkeerd - klik ergens op de pagina',
        'InvalidStateError': 'Audio systeem niet beschikbaar',
        'default': 'Audio systeem fout'
      }
    };

    const messages = friendlyMessages[operation] || friendlyMessages.playback;
    const friendlyMessage = messages[error.name] || messages.default;
    
    const userError = new Error(friendlyMessage);
    userError.originalError = error;
    userError.operation = operation;
    userError.suggestion = this._getErrorSuggestion(operation, error);
    userError.recoverable = this._isRecoverableError(operation, error);
    userError.timestamp = new Date().toISOString();
    
    return userError;
  }

  /**
   * Get error recovery suggestions with specific actions
   * @param {string} operation - The operation that failed
   * @param {Error} error - Original error
   * @returns {string} Recovery suggestion
   * @private
   */
  _getErrorSuggestion(operation, error) {
    const suggestions = {
      decode: {
        'EncodingError': 'Probeer de verbinding te vernieuwen of gebruik een andere browser',
        'DataError': 'Controleer uw internetverbinding en probeer opnieuw',
        'NotSupportedError': 'Upgrade naar Chrome, Firefox of Safari voor betere ondersteuning',
        'NetworkError': 'Controleer uw internetverbinding en herlaad de pagina',
        'TimeoutError': 'Sluit andere audio applicaties en probeer opnieuw',
        'default': this.recoveryMode ? 'Systeem herstelt zich - even geduld' : 'Herlaad de pagina en probeer opnieuw'
      },
      playback: {
        'InvalidStateError': 'Wacht even en probeer opnieuw, of herlaad de pagina',
        'NotAllowedError': 'Klik ergens op de pagina om audio toe te staan, dan opnieuw proberen',
        'NotSupportedError': 'Upgrade naar een moderne browser met Web Audio ondersteuning',
        'NetworkError': 'Controleer uw verbinding en herstart de luistersessie',
        'default': 'Controleer uw audio instellingen en herlaad indien nodig'
      },
      context: {
        'NotAllowedError': 'Klik ergens op de pagina en probeer opnieuw te luisteren',
        'InvalidStateError': 'Herlaad de pagina om het audio systeem te herstarten',
        'default': 'Herstart uw browser en probeer opnieuw'
      }
    };

    const operationSuggestions = suggestions[operation] || suggestions.playback;
    let suggestion = operationSuggestions[error.name] || operationSuggestions.default;
    
    // Add recovery mode context
    if (this.recoveryMode) {
      suggestion += ' (Herstel modus actief - prestaties tijdelijk beperkt)';
    }
    
    // Add specific suggestions based on consecutive failures
    if (this.consecutiveFailures > 5) {
      suggestion += ' - Overweeg de pagina te herladen voor een volledige reset';
    }
    
    return suggestion;
  }

  /**
   * Check if an error is recoverable
   * @param {string} operation - The operation that failed
   * @param {Error} error - Original error
   * @returns {boolean} True if error is recoverable
   * @private
   */
  _isRecoverableError(operation, error) {
    const recoverableErrors = {
      decode: ['NetworkError', 'TimeoutError', 'DataError'],
      playback: ['InvalidStateError', 'NetworkError'],
      context: ['NotAllowedError', 'InvalidStateError']
    };
    
    const recoverable = recoverableErrors[operation] || [];
    return recoverable.includes(error.name);
  }

  /**
   * Get comprehensive audio system health report
   * @returns {object} Health report with diagnostics and troubleshooting
   */
  getHealthReport() {
    const report = {
      timestamp: new Date().toISOString(),
      overall: this._getOverallHealth(),
      audioContext: {
        state: this.audioContext?.state || 'not_initialized',
        sampleRate: this.audioContext?.sampleRate || 0,
        currentTime: this.audioContext?.currentTime || 0,
        baseLatency: this.audioContext?.baseLatency || 0,
        outputLatency: this.audioContext?.outputLatency || 0
      },
      playback: {
        isPlaying: this.isPlaying,
        isStreaming: this.isStreaming,
        queueSize: this.audioQueue.length,
        queueDuration: this.getQueueDuration(),
        activeSources: this.activeSources.length,
        nextPlaybackTime: this.nextPlaybackTime
      },
      performance: this.getPerformanceMetrics(),
      memory: {
        queueMemory: this._getCurrentQueueMemory(),
        bufferPoolSize: this.bufferPool.length,
        estimatedTotal: this._getCurrentQueueMemory() + (this.bufferPool.length * 1024 * 1024),
        memoryPressure: this._isMemoryPressure()
      },
      quality: this.getPlaybackQuality(),
      errors: {
        droppedChunks: this.performanceMetrics.droppedChunks,
        successRate: this.performanceMetrics.processedChunks > 0 ? 
          ((this.performanceMetrics.processedChunks / (this.performanceMetrics.processedChunks + this.performanceMetrics.droppedChunks)) * 100).toFixed(2) + '%' : 'N/A',
        recentErrors: this._getRecentErrors()
      },
      diagnostics: this._generateDiagnostics(),
      troubleshooting: this._getTroubleshootingSteps()
    };

    // Add browser memory info if available
    if (typeof performance.memory !== 'undefined') {
      report.browser = {
        memoryUsage: Math.round(performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit * 100) + '%',
        memoryUsed: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) + 'MB',
        memoryLimit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024) + 'MB',
        memoryPressure: performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit > 0.8
      };
    }

    return report;
  }

  /**
   * Get overall system health status
   * @returns {string} Health status
   * @private
   */
  _getOverallHealth() {
    const issues = [];
    
    if (!this.audioContext || this.audioContext.state === 'suspended') {
      issues.push('AudioContext not active');
    }
    
    if (this.performanceMetrics.droppedChunks > this.performanceMetrics.processedChunks * 0.1) {
      issues.push('High drop rate');
    }
    
    if (this._isMemoryPressure()) {
      issues.push('Memory pressure');
    }
    
    if (this.audioQueue.length > this.maxQueueSize * 0.9) {
      issues.push('Queue overload');
    }
    
    if (issues.length === 0) return 'Healthy';
    if (issues.length <= 2) return 'Warning';
    return 'Critical';
  }

  /**
   * Get recent error history
   * @returns {Array} Recent errors
   * @private
   */
  _getRecentErrors() {
    if (!this.errorHistory) {
      this.errorHistory = [];
    }
    
    // Return last 5 errors from the last 5 minutes
    const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);
    return this.errorHistory
      .filter(error => error.timestamp > fiveMinutesAgo)
      .slice(-5);
  }

  /**
   * Log error to history
   * @param {Error} error - Error to log
   * @param {string} operation - Operation that failed
   * @private
   */
  _logError(error, operation) {
    if (!this.errorHistory) {
      this.errorHistory = [];
    }
    
    this.errorHistory.push({
      timestamp: Date.now(),
      operation,
      error: error.name,
      message: error.message,
      recoverable: this._isRecoverableError(operation, error)
    });
    
    // Keep only last 20 errors
    if (this.errorHistory.length > 20) {
      this.errorHistory = this.errorHistory.slice(-20);
    }
  }

  /**
   * Generate system diagnostics
   * @returns {object} Diagnostic information
   * @private
   */
  _generateDiagnostics() {
    return {
      webAudioSupport: AudioPlayer.isSupported(),
      audioContextState: this.audioContext?.state || 'not_initialized',
      browserCapabilities: {
        decodeAudioData: typeof this.audioContext?.decodeAudioData === 'function',
        createBufferSource: typeof this.audioContext?.createBufferSource === 'function',
        destination: !!this.audioContext?.destination
      },
      systemLoad: {
        queueUtilization: (this.audioQueue.length / this.maxQueueSize * 100).toFixed(1) + '%',
        memoryUtilization: this._isMemoryPressure() ? 'High' : 'Normal',
        activeProcesses: this.activeSources.length
      }
    };
  }

  /**
   * Get troubleshooting steps based on current state
   * @returns {Array} Troubleshooting recommendations
   * @private
   */
  _getTroubleshootingSteps() {
    const steps = [];
    
    if (!this.audioContext) {
      steps.push('Initialize AudioContext by calling createAudioContext()');
    } else if (this.audioContext.state === 'suspended') {
      steps.push('Resume AudioContext - klik ergens op de pagina');
    }
    
    if (this.performanceMetrics.droppedChunks > 5) {
      steps.push('Hoge drop rate - controleer internetverbinding');
    }
    
    if (this._isMemoryPressure()) {
      steps.push('Geheugendruk - herlaad de pagina om geheugen vrij te maken');
    }
    
    if (this.audioQueue.length > this.maxQueueSize * 0.8) {
      steps.push('Grote wachtrij - mogelijk trage verwerking');
    }
    
    if (this.activeSources.length > 10) {
      steps.push('Veel actieve bronnen - mogelijk geheugenlek');
    }
    
    if (this.consecutiveFailures > 5) {
      steps.push('Herhaalde fouten - herstart audio systeem');
    }
    
    if (this.recoveryMode) {
      steps.push('Herstel modus actief - prestaties tijdelijk beperkt');
    }
    
    if (steps.length === 0) {
      steps.push('Systeem werkt normaal - geen actie vereist');
    }
    
    return steps;
  }

  /**
   * Validate decoded audio buffer
   * @param {AudioBuffer} audioBuffer - Audio buffer to validate
   * @returns {boolean} True if valid
   * @private
   */
  _isValidDecodedAudio(audioBuffer) {
    return audioBuffer && 
           audioBuffer.sampleRate > 0 && 
           audioBuffer.numberOfChannels > 0 && 
           audioBuffer.duration > 0 &&
           audioBuffer.duration < 30; // Reasonable max duration
  }

  /**
   * Update playback quality status
   * @param {string} status - Current playback status
   * @private
   */
  _updatePlaybackQuality(status) {
    this.playbackQuality = status;
    if (this.onQualityChange) {
      try {
        this.onQualityChange(status);
      } catch (error) {
        console.warn('Quality change callback error:', error);
      }
    }
  }

  /**
   * Notify error to user callback
   * @param {string} operation - Operation that failed
   * @param {Error} error - Error that occurred
   * @private
   */
  _notifyError(operation, error) {
    if (this.onError) {
      try {
        this.onError({
          operation,
          error: error.message,
          suggestion: this._getErrorSuggestion(operation, error),
          recoverable: this._isRecoverableError(operation, error),
          timestamp: new Date().toISOString()
        });
      } catch (callbackError) {
        console.warn('Error callback failed:', callbackError);
      }
    }
  }

  /**
   * Notify successful recovery to user callback
   * @param {string} operation - Operation that recovered
   * @private
   */
  _notifyRecovery(operation, failureCount = 0) {
    if (this.onRecovery) {
      try {
        this.onRecovery({
          operation,
          message: `${operation} hersteld na ${failureCount} fouten`,
          timestamp: new Date().toISOString()
        });
      } catch (callbackError) {
        console.warn('Recovery callback failed:', callbackError);
      }
    }
  }

  /**
   * Get playback quality metrics
   * @returns {object} Quality metrics
   */
  getPlaybackQuality() {
    const metrics = this.getPerformanceMetrics();
    
    return {
      overall: this._calculateOverallQuality(metrics),
      latency: this._assessLatency(metrics),
      stability: this._assessStability(metrics),
      memory: this._assessMemoryUsage(metrics),
      recommendations: this._getQualityRecommendations(metrics)
    };
  }

  /**
   * Calculate overall quality score
   * @param {object} metrics - Performance metrics
   * @returns {string} Quality rating
   * @private
   */
  _calculateOverallQuality(metrics) {
    let score = 100;
    
    // Penalize high drop rate
    const dropRate = metrics.droppedChunks / (metrics.processedChunks + metrics.droppedChunks);
    score -= dropRate * 50;
    
    // Penalize high latency
    if (metrics.avgLatency > 100) score -= 20;
    if (metrics.avgLatency > 200) score -= 20;
    
    // Penalize memory pressure
    if (this._isMemoryPressure()) score -= 15;
    
    if (score >= 90) return 'Excellent';
    if (score >= 75) return 'Good';
    if (score >= 60) return 'Fair';
    return 'Poor';
  }

  /**
   * Assess latency performance
   * @param {object} metrics - Performance metrics
   * @returns {string} Latency assessment
   * @private
   */
  _assessLatency(metrics) {
    if (!metrics.avgLatency) return 'Unknown';
    if (metrics.avgLatency < 50) return 'Excellent';
    if (metrics.avgLatency < 100) return 'Good';
    if (metrics.avgLatency < 200) return 'Fair';
    return 'Poor';
  }

  /**
   * Assess playback stability
   * @param {object} metrics - Performance metrics
   * @returns {string} Stability assessment
   * @private
   */
  _assessStability(metrics) {
    const dropRate = metrics.droppedChunks / (metrics.processedChunks + metrics.droppedChunks);
    if (dropRate < 0.01) return 'Excellent';
    if (dropRate < 0.05) return 'Good';
    if (dropRate < 0.1) return 'Fair';
    return 'Poor';
  }

  /**
   * Assess memory usage
   * @param {object} metrics - Performance metrics
   * @returns {string} Memory assessment
   * @private
   */
  _assessMemoryUsage(metrics) {
    if (this._isMemoryPressure()) return 'High';
    if (metrics.currentQueueMemory > this.maxQueueMemory * 0.7) return 'Moderate';
    return 'Low';
  }

  /**
   * Get quality improvement recommendations
   * @param {object} metrics - Performance metrics
   * @returns {string[]} Recommendations
   * @private
   */
  _getQualityRecommendations(metrics) {
    const recommendations = [];
    
    const dropRate = metrics.droppedChunks / (metrics.processedChunks + metrics.droppedChunks);
    if (dropRate > 0.05) {
      recommendations.push('Hoge drop rate - controleer internetverbinding');
    }
    
    if (metrics.avgLatency > 200) {
      recommendations.push('Hoge latency - sluit andere audio applicaties');
    }
    
    if (this._isMemoryPressure()) {
      recommendations.push('Hoog geheugenverbruik - herlaad de pagina');
    }
    
    if (this.audioQueue.length > this.maxQueueSize * 0.8) {
      recommendations.push('Grote audio wachtrij - mogelijk trage verwerking');
    }
    
    if (recommendations.length === 0) {
      recommendations.push('Audio kwaliteit is goed');
    }
    
    return recommendations;
  }

  /**
   * Play a single audio buffer with comprehensive error recovery
   * @param {AudioBuffer} audioBuffer - Audio buffer to play
   * @returns {Promise} Promise that resolves when audio finishes
   */
  async playAudioBuffer(audioBuffer) {
    if (!this.audioContext) {
      const error = new Error('AudioContext not initialized');
      this._logError(error, 'playback');
      this._notifyError('context', error);
      throw this._createUserFriendlyError('context', error);
    }

    if (!audioBuffer) {
      const error = new Error('AudioBuffer is required');
      this._logError(error, 'playback');
      throw this._createUserFriendlyError('playback', error);
    }

    let retryCount = 0;
    const maxRetries = this.recoveryMode ? 1 : 2;
    let lastError;
    
    while (retryCount <= maxRetries) {
      try {
        // Handle AudioContext suspension with recovery
        if (this.audioContext.state === 'suspended') {
          try {
            await this._resumeAudioContext();
          } catch (resumeError) {
            this._logError(resumeError, 'context');
            this._notifyError('context', resumeError);
            throw this._createUserFriendlyError('context', resumeError);
          }
        }

        return new Promise((resolve, reject) => {
          let source;
          let timeoutId;
          
          try {
            source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);

            this.isPlaying = true;
            this.currentPlaybackTime = this.audioContext.currentTime;
            this._updatePlaybackQuality('playing');

            // Set timeout for playback
            timeoutId = setTimeout(() => {
              this.isPlaying = false;
              if (source) {
                try { source.stop(); } catch (e) { /* ignore */ }
              }
              const error = new Error('Playback timeout');
              this._logError(error, 'playback');
              this._notifyError('playback', error);
              reject(this._createUserFriendlyError('playback', error));
            }, (audioBuffer.duration + 1) * 1000);

            source.onended = () => {
              clearTimeout(timeoutId);
              this.isPlaying = false;
              this._updatePlaybackQuality('idle');
              if (this.onPlaybackComplete) {
                try {
                  this.onPlaybackComplete();
                } catch (callbackError) {
                  console.warn('Playback completion callback error:', callbackError);
                }
              }
              resolve();
            };

            source.onerror = (error) => {
              clearTimeout(timeoutId);
              this.isPlaying = false;
              this._updatePlaybackQuality('error');
              this._logError(error, 'playback');
              this._notifyError('playback', error);
              reject(this._createUserFriendlyError('playback', error));
            };

            source.start();
          } catch (error) {
            clearTimeout(timeoutId);
            this.isPlaying = false;
            this._updatePlaybackQuality('error');
            this._logError(error, 'playback');
            reject(this._createUserFriendlyError('playback', error));
          }
        });
      } catch (error) {
        lastError = error;
        retryCount++;
        
        this._logError(error, 'playback');
        
        if (retryCount > maxRetries) {
          this.isPlaying = false;
          this._notifyError('playback', error);
          throw this._createUserFriendlyError('playback', error);
        }
        
        // Wait before retry with exponential backoff
        await new Promise(resolve => setTimeout(resolve, 500 * retryCount));
      }
    }
  }

  /**
   * Start continuous stream playback
   */
  startStreamPlayback() {
    if (!this.audioContext) {
      throw new Error('AudioContext not initialized');
    }

    if (this.isStreaming) {
      return;
    }

    this.isStreaming = true;
    this.nextPlaybackTime = this.audioContext.currentTime;
    this._processAudioQueue();
  }

  /**
   * Stop continuous stream playback with cleanup
   */
  stopStreamPlayback() {
    this.isStreaming = false;
    
    // Stop all active sources
    this.activeSources.forEach(source => {
      try {
        source.stop();
      } catch (error) {
        // Source may already be stopped
      }
    });
    
    this.activeSources = [];
    this.nextPlaybackTime = 0;
    
    // Performance cleanup
    this._performCleanup();
  }

  /**
   * Perform cleanup for memory management
   * @private
   */
  _performCleanup() {
    // Return queued buffers to pool
    while (this.audioQueue.length > 0) {
      const buffer = this.audioQueue.shift();
      this._returnBufferToPool(buffer);
    }
    
    // Clean up buffer pool if too large
    if (this.bufferPool.length > this.maxPoolSize) {
      this.bufferPool.splice(this.maxPoolSize);
    }
    
    // Force garbage collection hint (if available)
    if (typeof window !== 'undefined' && window.gc) {
      window.gc();
    }
  }

  /**
   * Process audio queue for streaming playback with optimization
   * @private
   */
  _processAudioQueue() {
    if (!this.isStreaming) {
      return;
    }

    const currentTime = performance.now();
    const timeSinceLastProcess = currentTime - this.lastProcessTime;
    
    // Adaptive processing interval based on queue size
    const queueSize = this.audioQueue.length;
    let processInterval = 50; // Default 50ms
    
    if (queueSize > this.maxQueueSize * 0.8) {
      processInterval = 25; // Faster processing when queue is full
    } else if (queueSize < this.maxQueueSize * 0.2) {
      processInterval = 100; // Slower processing when queue is low
    }

    const audioBuffer = this.getNextFromQueue();
    if (audioBuffer) {
      this._scheduleAudioBuffer(audioBuffer);
      this._recordLatency(currentTime);
    }
    
    this.lastProcessTime = currentTime;

    // Continue processing queue with adaptive interval
    setTimeout(() => this._processAudioQueue(), processInterval);
  }

  /**
   * Schedule audio buffer for precise playback
   * @param {AudioBuffer} audioBuffer - Audio buffer to schedule
   * @private
   */
  _scheduleAudioBuffer(audioBuffer) {
    try {
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);

      // Calculate when to start this chunk
      const currentTime = this.audioContext.currentTime;
      const startTime = Math.max(currentTime, this.nextPlaybackTime);
      
      // Update next playback time for seamless transitions
      this.nextPlaybackTime = startTime + audioBuffer.duration;

      source.onended = () => {
        // Remove from active sources
        const index = this.activeSources.indexOf(source);
        if (index > -1) {
          this.activeSources.splice(index, 1);
        }
      };

      this.activeSources.push(source);
      source.start(startTime);
    } catch (error) {
      console.error('Failed to schedule audio buffer:', error);
    }
  }
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AudioPlayer };
}

if (typeof window !== 'undefined') {
  window.AudioPlayer = AudioPlayer;
}