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

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    requestMicrophoneAccess,
    stopAudioStream
  };
}

if (typeof window !== 'undefined') {
  window.AppAudio = {
    requestMicrophoneAccess,
    stopAudioStream
  };
}