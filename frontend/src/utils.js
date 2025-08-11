/**
 * Utility Functions Module
 * Common helper functions and browser compatibility checks
 */

/**
 * Check if WebSocket is supported
 * @returns {boolean} True if WebSocket is supported
 */
function isWebSocketSupported() {
  return typeof WebSocket !== 'undefined';
}

/**
 * Check if MediaRecorder is supported
 * @returns {boolean} True if MediaRecorder is supported
 */
function isMediaRecorderSupported() {
  return typeof MediaRecorder !== 'undefined';
}

/**
 * Check if getUserMedia is supported
 * @returns {boolean} True if getUserMedia is supported
 */
function isGetUserMediaSupported() {
  return !!(typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

/**
 * Check audio support capabilities
 * @returns {object} Audio support status
 */
function checkAudioSupport() {
  return {
    mediaRecorder: isMediaRecorderSupported(),
    getUserMedia: isGetUserMediaSupported(),
    webAudio: typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined'
  };
}

/**
 * Check if browser supports required features
 * @returns {object} Feature support status
 */
function checkBrowserSupport() {
  const audioSupport = checkAudioSupport();
  return {
    webSocket: isWebSocketSupported(),
    localStorage: typeof Storage !== 'undefined',
    addEventListener: typeof document.addEventListener !== 'undefined',
    querySelector: typeof document.querySelector !== 'undefined',
    ...audioSupport
  };
}

/**
 * Show browser compatibility warning if needed
 */
function showCompatibilityWarning() {
  const support = checkBrowserSupport();
  const warnings = [];
  
  if (!support.webSocket) {
    warnings.push('WebSocket wordt niet ondersteund door uw browser.');
  }
  
  if (!support.getUserMedia) {
    warnings.push('Microfoon toegang wordt niet ondersteund door uw browser.');
  }
  
  if (!support.mediaRecorder) {
    warnings.push('Audio opname wordt niet ondersteund door uw browser.');
  }
  
  if (warnings.length > 0) {
    const warning = document.createElement('div');
    warning.style.cssText = 'background: #f8d7da; color: #721c24; padding: 10px; margin: 10px 0; border-radius: 5px;';
    warning.innerHTML = `<strong>Browser Compatibiliteit:</strong><br>${warnings.join('<br>')}<br><em>Upgrade naar een moderne browser voor volledige functionaliteit.</em>`;
    document.body.insertBefore(warning, document.body.firstChild);
  }
}

/**
 * Debounce function to prevent rapid button clicks
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, delay) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

/**
 * Log error with context
 * @param {string} context - Error context
 * @param {Error} error - Error object
 */
function logError(context, error) {
  console.error(`[${context}]`, error);
}

// Export for modules and browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { 
    isWebSocketSupported,
    isMediaRecorderSupported,
    isGetUserMediaSupported,
    checkAudioSupport,
    checkBrowserSupport, 
    showCompatibilityWarning,
    debounce,
    logError
  };
}

if (typeof window !== 'undefined') {
  window.AppUtils = { 
    isWebSocketSupported,
    isMediaRecorderSupported,
    isGetUserMediaSupported,
    checkAudioSupport,
    checkBrowserSupport, 
    showCompatibilityWarning,
    debounce,
    logError
  };
}