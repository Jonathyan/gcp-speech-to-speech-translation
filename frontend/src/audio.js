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
 * AudioRecorder class for handling MediaRecorder functionality
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
    
    // Get configuration
    const chunkConfig = window.AppConfig ? 
      window.AppConfig.getAudioChunkConfig() : 
      { intervalMs: 250 };
    
    // Determine best audio format
    const mimeType = options.mimeType || this.getBestAudioFormat();
    const timeslice = options.timeslice || chunkConfig.intervalMs;
    
    // Create MediaRecorder
    this.mediaRecorder = new MediaRecorder(stream, {
      mimeType: mimeType,
      timeslice: timeslice
    });
    
    this.timeslice = timeslice;
    
    // Setup event handlers
    this.setupEventHandlers();
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
  start() {
    if (!this.isRecording) {
      this.mediaRecorder.start(this.timeslice);
      this.isRecording = true;
    }
  }
  
  /**
   * Stop recording
   */
  stop() {
    if (this.isRecording) {
      this.mediaRecorder.stop();
      this.isRecording = false;
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
    if (!blob || blob.size === 0) {
      reject(new Error('Audio data is empty'));
      return;
    }
    
    const reader = new FileReader();
    
    reader.onload = () => {
      resolve(reader.result);
    };
    
    reader.onerror = () => {
      reject(new Error('Failed to convert audio chunk'));
    };
    
    try {
      reader.readAsArrayBuffer(blob);
    } catch (error) {
      reject(new Error('Failed to convert audio chunk'));
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
    return {
      isValid: false,
      size: 0,
      error: 'Invalid audio data'
    };
  }
  
  const size = arrayBuffer.byteLength;
  const minSize = 100; // 100 bytes minimum
  
  // Get max size from config
  const chunkConfig = window.AppConfig ? 
    window.AppConfig.getAudioChunkConfig() : 
    { maxSize: 100 * 1024 };
  const maxSize = chunkConfig.maxSize;
  
  if (size < minSize) {
    return {
      isValid: false,
      size: size,
      error: `Audio chunk too small (${size} bytes)`
    };
  }
  
  if (size > maxSize) {
    return {
      isValid: false,
      size: size,
      error: `Audio chunk too large (${size} bytes)`
    };
  }
  
  return {
    isValid: true,
    size: size,
    error: null
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