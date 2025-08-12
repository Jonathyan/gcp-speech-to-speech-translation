/**
 * Audio Management Module
 * Handles microphone access and audio stream management
 */

/**
 * Request microphone access from user
 * @returns {Promise<{success: boolean, stream: MediaStream|null, error: string|undefined}>}
 */
async function requestMicrophoneAccess() {
  try {
    // Check if getUserMedia is supported
    if (!navigator || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return {
        success: false,
        stream: null,
        error: 'Microphone access not supported'
      };
    }
    
    // Request microphone access
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    return {
      success: true,
      stream: stream,
      error: undefined
    };
    
  } catch (error) {
    let errorMessage = 'Unknown error';
    
    switch (error.name) {
      case 'NotAllowedError':
        errorMessage = 'Permission denied';
        break;
      case 'NotFoundError':
        errorMessage = 'No microphone found';
        break;
      case 'NotReadableError':
        errorMessage = 'Microphone already in use';
        break;
      default:
        errorMessage = error.message || 'Microphone access failed';
    }
    
    console.error('Microphone access error:', error);
    
    return {
      success: false,
      stream: null,
      error: errorMessage
    };
  }
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
    
    // Determine best audio format
    const mimeType = options.mimeType || this.getBestAudioFormat();
    const timeslice = options.timeslice || 250;
    
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
        this.onDataCallback(event.data);
      }
    };
    
    this.mediaRecorder.onerror = (error) => {
      console.error('MediaRecorder error:', error);
      this.isRecording = false;
      if (this.onErrorCallback) {
        this.onErrorCallback(error);
      }
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
  const maxSize = 100 * 1024; // 100KB maximum
  
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
    validateAudioChunk
  };
}

if (typeof window !== 'undefined') {
  window.AppAudio = {
    requestMicrophoneAccess,
    stopAudioStream,
    AudioRecorder,
    convertAudioChunk,
    validateAudioChunk
  };
}