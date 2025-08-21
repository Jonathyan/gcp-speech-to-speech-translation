/**
 * Audio Management Module
 * Handles microphone access and audio stream management
 */

/**
 * Request microphone access from user with retry logic
 * @param {number} maxRetries - Maximum retry attempts
 * @returns {Promise<{success: boolean, stream: MediaStream|null, error: string|undefined, suggestion?: string}>}
 */
async function requestMicrophoneAccess(maxRetries = 2) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // Check if getUserMedia is supported
      if (!navigator || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        return {
          success: false,
          stream: null,
          error: 'Microfoon toegang wordt niet ondersteund door uw browser',
          suggestion: 'Upgrade naar een moderne browser zoals Chrome, Firefox of Safari'
        };
      }
      
      // Get audio constraints from config with fallback
      let constraints;
      try {
        constraints = window.AppConfig ? 
          window.AppConfig.getAudioConstraints() : 
          { audio: true };
      } catch (configError) {
        console.warn('Config error, using fallback constraints:', configError);
        constraints = { audio: true };
      }
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      return {
        success: true,
        stream: stream,
        error: undefined
      };
      
    } catch (error) {
      console.error(`Microphone access attempt ${attempt + 1}/${maxRetries + 1} failed:`, error);
      
      // If this is the last attempt, return user-friendly error
      if (attempt === maxRetries) {
        const friendlyError = createMicrophoneError(error);
        return {
          success: false,
          stream: null,
          ...friendlyError
        };
      }
      
      // Wait before retry (except for permission errors)
      if (error.name !== 'NotAllowedError') {
        await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
      } else {
        // Don't retry permission errors
        const friendlyError = createMicrophoneError(error);
        return {
          success: false,
          stream: null,
          ...friendlyError
        };
      }
    }
  }
}

/**
 * Create user-friendly microphone error messages
 * @param {Error} error - Original error
 * @returns {object} User-friendly error object
 */
function createMicrophoneError(error) {
  const friendlyErrors = {
    'NotAllowedError': {
      error: 'Microfoon toegang werd geweigerd',
      suggestion: 'Klik op het microfoon icoon in uw browser en sta toegang toe. Herlaad daarna de pagina.'
    },
    'NotFoundError': {
      error: 'Geen microfoon gevonden',
      suggestion: 'Controleer of uw microfoon is aangesloten en probeer opnieuw.'
    },
    'NotReadableError': {
      error: 'Microfoon is al in gebruik',
      suggestion: 'Sluit andere applicaties die uw microfoon gebruiken en probeer opnieuw.'
    },
    'OverconstrainedError': {
      error: 'Microfoon voldoet niet aan de vereisten',
      suggestion: 'Uw microfoon ondersteunt niet de gevraagde audio kwaliteit. Probeer een andere microfoon.'
    },
    'AbortError': {
      error: 'Microfoon toegang werd onderbroken',
      suggestion: 'Probeer opnieuw. Als het probleem aanhoudt, herstart uw browser.'
    }
  };
  
  return friendlyErrors[error.name] || {
    error: 'Microfoon toegang mislukt',
    suggestion: 'Controleer uw microfoon instellingen en probeer opnieuw. Als het probleem aanhoudt, herstart uw browser.'
  };
}

/**
 * Stop audio stream and cleanup
 * @param {MediaStream|null} stream - Audio stream to stop
 */
function stopAudioStream(stream) {
  if (!stream) {
    return;
  }
  
  try {
    const tracks = stream.getTracks();
    tracks.forEach(track => {
      track.stop();
    });
  } catch (error) {
    console.error('Error stopping audio stream:', error);
  }
}

/**
 * Enhanced AudioRecorder class supporting both MediaRecorder and Web Audio API
 * Automatically chooses the best recording method for optimal compatibility
 */
class AudioRecorder {
  constructor(stream, options = {}) {
    this.stream = stream;
    this.isRecording = false;
    this.onDataCallback = options.onDataAvailable || null;
    this.onErrorCallback = options.onError || null;
    this.retryCount = 0;
    this.maxRetries = options.maxRetries || 3;
    this.retryDelay = options.retryDelay || 1000;
    
    // Phase 2: Choose recording method (Professional WAV encoder vs MediaRecorder)
    this.useWebAudioAPI = options.useWebAudioAPI !== false; // Default to true
    this.recorder = null;
    
    // Get configuration
    const chunkConfig = window.AppConfig ? 
      window.AppConfig.getAudioChunkConfig() : 
      { chunkIntervalMs: 250, chunkSize: 2048, maxSize: 150 * 1024 };
    
    if (this.useWebAudioAPI && window.ProfessionalAudioRecorder) {
      // Phase 3: Use Web Audio API with optimized configuration
      this.recorder = new window.ProfessionalAudioRecorder(chunkConfig);
      this.recorder.setOnDataAvailable((event) => {
        console.log(`📡 AudioRecorder received callback:`, event);
        if (this.onDataCallback && event.data && event.data.size > 0) {
          console.log(`📤 Forwarding ${event.data.size} bytes to UI callback`);
          console.log(`🔍 UI Callback type:`, typeof this.onDataCallback);
          console.log(`🔍 Calling UI callback with:`, event.data);
          // ProfessionalAudioRecorder sends { data: blob }, make it compatible with MediaRecorder format
          try {
            this.onDataCallback(event.data);
            console.log(`✅ UI callback executed successfully`);
          } catch (error) {
            console.error(`❌ UI callback execution failed:`, error);
          }
        } else {
          console.warn('⚠️ AudioRecorder: No callback or empty data', {
            hasCallback: !!this.onDataCallback,
            hasData: !!event.data,
            dataSize: event.data?.size
          });
        }
      });
      console.log(`Using Professional Audio Recorder with optimized config: ${chunkConfig.chunkIntervalMs}ms chunks`);
    } else {
      // Fallback: Use MediaRecorder
      const mimeType = options.mimeType || this.getBestAudioFormat();
      const timeslice = options.timeslice || chunkConfig.chunkIntervalMs;
      
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        timeslice: timeslice
      });
      
      this.timeslice = timeslice;
      this.setupEventHandlers();
      console.log('Using MediaRecorder fallback');
    }
  }
  
  /**
   * Get best supported audio format
   * @returns {string} MIME type
   */
  getBestAudioFormat() {
    // Use config if available
    if (window.AppConfig && window.AppConfig.getBestAudioFormat) {
      try {
        return window.AppConfig.getBestAudioFormat();
      } catch (error) {
        console.warn('Config audio format detection failed, using fallback');
      }
    }
    
    // Fallback to original logic
    const formats = ['audio/webm', 'audio/mp4', 'audio/wav'];
    
    for (const format of formats) {
      if (MediaRecorder.isTypeSupported(format)) {
        return format;
      }
    }
    
    throw new Error('No supported audio format found');
  }
  
  /**
   * Setup MediaRecorder event handlers
   */
  setupEventHandlers() {
    this.mediaRecorder.ondataavailable = (event) => {
      if (this.onDataCallback && event.data.size > 0) {
        // Record performance metrics
        if (window.AppDiagnostics) {
          window.AppDiagnostics.performanceMetrics.recordAudioChunk(event.data.size, true);
        }
        this.onDataCallback(event.data);
      }
    };
    
    this.mediaRecorder.onerror = (error) => {
      console.error('MediaRecorder error:', error);
      this.isRecording = false;
      
      // Record performance metrics
      if (window.AppDiagnostics) {
        window.AppDiagnostics.performanceMetrics.recordAudioChunk(0, false);
      }
      
      // Attempt recovery
      this.handleRecordingError(error);
    };
  }
  
  /**
   * Handle recording errors with retry logic
   * @param {Error} error - The recording error
   */
  handleRecordingError(error) {
    if (this.retryCount < this.maxRetries) {
      this.retryCount++;
      console.warn(`Recording error, attempting retry ${this.retryCount}/${this.maxRetries}:`, error.message);
      
      setTimeout(() => {
        try {
          this.start();
        } catch (retryError) {
          console.error('Retry failed:', retryError);
          if (this.onErrorCallback) {
            this.onErrorCallback(this.createUserFriendlyError(error));
          }
        }
      }, this.retryDelay * this.retryCount);
    } else {
      console.error('Max retries exceeded for recording');
      if (this.onErrorCallback) {
        this.onErrorCallback(this.createUserFriendlyError(error));
      }
    }
  }
  
  /**
   * Create user-friendly error messages
   * @param {Error} error - Original error
   * @returns {object} User-friendly error object
   */
  createUserFriendlyError(error) {
    const friendlyErrors = {
      'InvalidStateError': {
        message: 'Opname kon niet worden gestart. Probeer opnieuw.',
        suggestion: 'Controleer of uw microfoon niet door een andere applicatie wordt gebruikt.'
      },
      'NotSupportedError': {
        message: 'Audio opname wordt niet ondersteund door uw browser.',
        suggestion: 'Upgrade naar een moderne browser zoals Chrome, Firefox of Safari.'
      },
      'SecurityError': {
        message: 'Microfoon toegang werd geweigerd.',
        suggestion: 'Klik op het microfoon icoon in uw browser en sta toegang toe.'
      }
    };
    
    const friendly = friendlyErrors[error.name] || {
      message: 'Er is een probleem opgetreden met de audio opname.',
      suggestion: 'Herlaad de pagina en probeer opnieuw.'
    };
    
    return {
      ...friendly,
      originalError: error.message,
      errorCode: error.name
    };
  }
  
  /**
   * Start recording
   */
  async start() {
    if (!this.isRecording) {
      try {
        if (this.recorder) {
          // Phase 2: Web Audio API recorder - pass the existing stream
          await this.recorder.startRecording(this.stream);
        } else {
          // Fallback: MediaRecorder
          this.mediaRecorder.start(this.timeslice);
        }
        this.isRecording = true;
      } catch (error) {
        console.error('Failed to start recording:', error);
        if (this.onErrorCallback) {
          this.onErrorCallback(this.createUserFriendlyError(error));
        }
      }
    }
  }
  
  /**
   * Stop recording
   */
  stop() {
    if (this.isRecording) {
      try {
        if (this.recorder) {
          // Phase 2: Web Audio API recorder
          this.recorder.stopRecording();
        } else {
          // Fallback: MediaRecorder
          this.mediaRecorder.stop();
        }
        this.isRecording = false;
      } catch (error) {
        console.error('Failed to stop recording:', error);
      }
    }
  }
}

/**
 * Convert audio Blob to ArrayBuffer
 * @param {Blob} blob - Audio blob to convert
 * @returns {Promise<ArrayBuffer>} Converted audio data
 */
function convertAudioChunk(blob) {
  return new Promise((resolve, reject) => {
    const startTime = performance.now();
    
    if (!blob || blob.size === 0) {
      console.error('🚫 Audio conversion failed: Empty blob', {
        hasBlob: !!blob,
        size: blob ? blob.size : 'N/A'
      });
      reject(new Error('Audio data is empty'));
      return;
    }
    
    console.log('🔄 Converting audio blob to ArrayBuffer:', {
      size: blob.size,
      type: blob.type,
      startTime: startTime.toFixed(2)
    });
    
    const reader = new FileReader();
    
    reader.onload = () => {
      const endTime = performance.now();
      const duration = (endTime - startTime).toFixed(2);
      console.log('✅ Audio conversion completed:', {
        inputSize: blob.size,
        outputSize: reader.result.byteLength,
        duration: duration + 'ms',
        format: 'ArrayBuffer'
      });
      resolve(reader.result);
    };
    
    reader.onerror = () => {
      const endTime = performance.now();
      const duration = (endTime - startTime).toFixed(2);
      console.error('❌ Audio conversion failed after', duration + 'ms');
      reject(new Error('Failed to convert audio chunk'));
    };
    
    try {
      reader.readAsArrayBuffer(blob);
    } catch (error) {
      console.error('❌ Audio conversion exception:', error);
      reject(new Error('Failed to convert audio chunk: ' + error.message));
    }
  });
}

/**
 * Validate audio chunk size and format
 * @param {ArrayBuffer} arrayBuffer - Audio data to validate
 * @returns {object} Validation result with isValid, size, and error
 */
function validateAudioChunk(arrayBuffer) {
  if (!arrayBuffer || !(arrayBuffer instanceof ArrayBuffer)) {
    console.error('🚫 Audio validation failed: Invalid ArrayBuffer', {
      isArrayBuffer: arrayBuffer instanceof ArrayBuffer,
      type: typeof arrayBuffer,
      hasData: !!arrayBuffer
    });
    return {
      isValid: false,
      size: 0,
      error: 'Invalid audio data - not ArrayBuffer'
    };
  }
  
  const size = arrayBuffer.byteLength;
  const minSize = 50; // Reduced minimum for frequent chunks
  
  // Get max size from config
  const chunkConfig = window.AppConfig ? 
    window.AppConfig.getAudioChunkConfig() : 
    { maxSize: 100 * 1024 };
  const maxSize = chunkConfig.maxSize;
  
  // Enhanced validation logging
  console.log('🔍 Validating audio chunk:', {
    size: size,
    minSize: minSize,
    maxSize: maxSize,
    sampleRate: '16kHz expected',
    format: 'LINEAR16 expected'
  });
  
  if (size < minSize) {
    console.warn('⚠️ Audio chunk too small:', size, 'bytes <', minSize, 'minimum');
    return {
      isValid: false,
      size: size,
      error: `Chunk too small: ${size} bytes < ${minSize} minimum`
    };
  }
  
  if (size > maxSize) {
    console.warn('⚠️ Audio chunk too large:', size, 'bytes >', maxSize, 'maximum');
    return {
      isValid: false,
      size: size,
      error: `Chunk too large: ${size} bytes > ${maxSize} maximum`
    };
  }
  
  // Log successful validation with timing info
  const timestamp = performance.now();
  console.log('✅ Audio chunk validation passed:', {
    size: size,
    sizeKB: (size / 1024).toFixed(2),
    timestamp: timestamp.toFixed(2),
    format: 'ready for Google Cloud Speech'
  });
  
  return {
    isValid: true,
    size: size,
    error: null,
    format: 'validated',
    timestamp: timestamp
  };
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    requestMicrophoneAccess,
    stopAudioStream,
    AudioRecorder,
    convertAudioChunk,
    validateAudioChunk,
    createMicrophoneError
  };
}

if (typeof window !== 'undefined') {
  window.AppAudio = {
    requestMicrophoneAccess,
    stopAudioStream,
    AudioRecorder,
    convertAudioChunk,
    validateAudioChunk,
    createMicrophoneError
  };
}