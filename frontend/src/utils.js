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
 * Check if browser supports required features
 * @returns {object} Feature support status
 */
function checkBrowserSupport() {
  return {
    webSocket: isWebSocketSupported(),
    localStorage: typeof Storage !== 'undefined',
    addEventListener: typeof document.addEventListener !== 'undefined',
    querySelector: typeof document.querySelector !== 'undefined'
  };
}

/**
 * Show browser compatibility warning if needed
 */
function showCompatibilityWarning() {
  const support = checkBrowserSupport();
  
  if (!support.webSocket) {
    const warning = document.createElement('div');
    warning.style.cssText = 'background: #f8d7da; color: #721c24; padding: 10px; margin: 10px 0; border-radius: 5px;';
    warning.textContent = 'WebSocket wordt niet ondersteund door uw browser. Upgrade naar een moderne browser.';
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
    checkBrowserSupport, 
    showCompatibilityWarning,
    debounce,
    logError
  };
}

if (typeof window !== 'undefined') {
  window.AppUtils = { 
    isWebSocketSupported, 
    checkBrowserSupport, 
    showCompatibilityWarning,
    debounce,
    logError
  };
}