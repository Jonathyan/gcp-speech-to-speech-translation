import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import traceback
from functools import wraps


class ErrorSeverity(Enum):
    """Classification of error severity levels."""
    LOW = "low"           # Recoverable errors, continue operation
    MEDIUM = "medium"     # Retry with backoff, may degrade service
    HIGH = "high"         # Fall back to alternative approach
    CRITICAL = "critical" # Stop processing, alert administrators


class ErrorCategory(Enum):
    """Categories of errors for targeted handling."""
    AUDIO_FORMAT = "audio_format"
    GOOGLE_API = "google_api"
    NETWORK = "network"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorEvent:
    """Represents an error event with context."""
    timestamp: float
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    stack_trace: Optional[str]
    context: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_successful: bool = False


class RecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def __init__(self, name: str, max_attempts: int = 3, backoff_factor: float = 2.0):
        self.name = name
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.attempt_count = 0
        self.last_attempt_time = 0.0
        self._logger = logging.getLogger(__name__)
    
    async def attempt_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Attempt to recover from the error.
        
        Returns:
            True if recovery was successful, False otherwise
        """
        if self.attempt_count >= self.max_attempts:
            self._logger.warning(f"Recovery strategy {self.name} exhausted attempts")
            return False
        
        # Exponential backoff
        if self.attempt_count > 0:
            wait_time = self.backoff_factor ** (self.attempt_count - 1)
            await asyncio.sleep(wait_time)
        
        self.attempt_count += 1
        self.last_attempt_time = time.time()
        
        try:
            result = await self._execute_recovery(error, context)
            if result:
                self._logger.info(f"Recovery strategy {self.name} successful on attempt {self.attempt_count}")
                self.reset()
            return result
        except Exception as recovery_error:
            self._logger.error(f"Recovery strategy {self.name} failed: {recovery_error}")
            return False
    
    async def _execute_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Override this method to implement specific recovery logic."""
        raise NotImplementedError("Recovery strategies must implement _execute_recovery")
    
    def reset(self):
        """Reset the strategy state after successful recovery."""
        self.attempt_count = 0
        self.last_attempt_time = 0.0
    
    def can_attempt(self) -> bool:
        """Check if recovery can be attempted."""
        return self.attempt_count < self.max_attempts


class FormatFallbackStrategy(RecoveryStrategy):
    """Recovery strategy for audio format issues."""
    
    def __init__(self):
        super().__init__("format_fallback", max_attempts=2)
        self.fallback_formats = ['linear16', 'webm', 'raw']
        self.current_format_index = 0
    
    async def _execute_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Try alternative audio format processing."""
        if self.current_format_index >= len(self.fallback_formats):
            return False
        
        fallback_format = self.fallback_formats[self.current_format_index]
        self.current_format_index += 1
        
        self._logger.info(f"Attempting format fallback to: {fallback_format}")
        
        # Update context with fallback format
        context['fallback_format'] = fallback_format
        context['force_format'] = True
        
        return True  # Recovery sets up context, actual fix happens in caller


class APIRetryStrategy(RecoveryStrategy):
    """Recovery strategy for Google Cloud API errors."""
    
    def __init__(self):
        super().__init__("api_retry", max_attempts=3, backoff_factor=1.5)
        self.api_error_codes = {
            400: ErrorSeverity.HIGH,     # Bad request - needs different approach
            401: ErrorSeverity.CRITICAL, # Auth error - stop processing  
            403: ErrorSeverity.CRITICAL, # Forbidden - stop processing
            429: ErrorSeverity.MEDIUM,   # Rate limited - retry with backoff
            500: ErrorSeverity.LOW,      # Server error - retry
            503: ErrorSeverity.LOW,      # Service unavailable - retry
        }
    
    async def _execute_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Retry API call with appropriate strategy."""
        # Extract status code if available
        status_code = getattr(error, 'code', None)
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            status_code = error.response.status_code
        
        if status_code in [401, 403]:
            self._logger.error(f"Authentication/authorization error {status_code}, cannot retry")
            return False
        
        if status_code == 429:
            # Rate limited - wait longer
            wait_time = self.backoff_factor ** self.attempt_count * 2
            self._logger.info(f"Rate limited, waiting {wait_time}s before retry")
            await asyncio.sleep(wait_time)
        
        self._logger.info(f"Retrying API call (attempt {self.attempt_count})")
        context['api_retry'] = True
        return True


class CircuitBreakerStrategy(RecoveryStrategy):
    """Recovery strategy using circuit breaker pattern."""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 30):
        super().__init__("circuit_breaker", max_attempts=1)
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "closed"  # closed, open, half_open
    
    async def _execute_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Implement circuit breaker logic."""
        current_time = time.time()
        
        if self.state == "closed":
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                self.last_failure_time = current_time
                self._logger.warning("Circuit breaker opened")
                return False
        
        elif self.state == "open":
            if current_time - self.last_failure_time >= self.reset_timeout:
                self.state = "half_open"
                self.failure_count = 0
                self._logger.info("Circuit breaker half-open, attempting recovery")
                return True
            return False
        
        elif self.state == "half_open":
            # Success will be handled externally by calling reset()
            return True
        
        return False
    
    def reset(self):
        """Reset circuit breaker on successful operation."""
        super().reset()
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
            self._logger.info("Circuit breaker closed")


class GracefulDegradationStrategy(RecoveryStrategy):
    """Recovery strategy that gracefully degrades service quality."""
    
    def __init__(self):
        super().__init__("graceful_degradation", max_attempts=1)
        self.degradation_levels = [
            "reduce_quality",
            "increase_buffer_time", 
            "disable_features",
            "fallback_mode"
        ]
        self.current_level = 0
    
    async def _execute_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Apply progressive service degradation."""
        if self.current_level >= len(self.degradation_levels):
            return False
        
        degradation = self.degradation_levels[self.current_level]
        self.current_level += 1
        
        self._logger.info(f"Applying graceful degradation: {degradation}")
        
        context['degradation_level'] = degradation
        
        if degradation == "reduce_quality":
            context['quality_threshold'] = 0.5  # Lower quality threshold
        elif degradation == "increase_buffer_time":
            context['min_duration'] = context.get('min_duration', 2.0) * 1.5
        elif degradation == "disable_features":
            context['disable_adaptive_timeout'] = True
            context['disable_silence_detection'] = True
        elif degradation == "fallback_mode":
            context['use_fallback_audio'] = True
        
        return True


class ErrorRecoveryManager:
    """Comprehensive error recovery manager."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # Error history
        self.error_history: List[ErrorEvent] = []
        self.max_history_size = 1000
        
        # Recovery strategies
        self.strategies: Dict[ErrorCategory, List[RecoveryStrategy]] = {
            ErrorCategory.AUDIO_FORMAT: [
                FormatFallbackStrategy(),
                GracefulDegradationStrategy()
            ],
            ErrorCategory.GOOGLE_API: [
                APIRetryStrategy(),
                CircuitBreakerStrategy(),
                GracefulDegradationStrategy()
            ],
            ErrorCategory.NETWORK: [
                APIRetryStrategy(),
                CircuitBreakerStrategy()
            ],
            ErrorCategory.TIMEOUT: [
                GracefulDegradationStrategy()
            ],
            ErrorCategory.RESOURCE: [
                GracefulDegradationStrategy()
            ],
            ErrorCategory.VALIDATION: [
                FormatFallbackStrategy()
            ]
        }
        
        # Statistics
        self.stats = {
            'total_errors': 0,
            'recovery_attempts': 0,
            'recovery_successes': 0,
            'errors_by_category': {cat.value: 0 for cat in ErrorCategory},
            'errors_by_severity': {sev.value: 0 for sev in ErrorSeverity}
        }
    
    def classify_error(self, error: Exception, context: Dict[str, Any]) -> Tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Google API errors
        if 'google' in error_type.lower() or 'grpc' in error_type.lower():
            if 'authentication' in error_msg or 'permission' in error_msg:
                return ErrorCategory.GOOGLE_API, ErrorSeverity.CRITICAL
            elif 'quota' in error_msg or 'rate limit' in error_msg:
                return ErrorCategory.GOOGLE_API, ErrorSeverity.MEDIUM
            elif 'bad encoding' in error_msg or 'invalid recognition' in error_msg:
                return ErrorCategory.AUDIO_FORMAT, ErrorSeverity.HIGH
            else:
                return ErrorCategory.GOOGLE_API, ErrorSeverity.MEDIUM
        
        # Audio format errors  
        if any(keyword in error_msg for keyword in ['encoding', 'format', 'audio', 'ffmpeg']):
            return ErrorCategory.AUDIO_FORMAT, ErrorSeverity.HIGH
        
        # Network errors (check before timeout to handle connection errors properly)
        if any(keyword in error_type.lower() for keyword in ['connection', 'network']):
            # If it contains timeout, classify as network timeout, not generic timeout
            if 'timeout' in error_msg:
                return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        # Handle ConnectionError specifically in message
        if 'connectionerror' in error_msg:
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        
        # Timeout errors (only for non-network timeouts)
        if 'timeout' in error_msg or 'TimeoutError' in error_type:
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
        
        # Resource errors
        if any(keyword in error_msg for keyword in ['memory', 'resource', 'limit']):
            return ErrorCategory.RESOURCE, ErrorSeverity.HIGH
        
        # Validation errors
        if any(keyword in error_type.lower() for keyword in ['value', 'validation', 'assertion']):
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW
        
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    async def handle_error(self, 
                          error: Exception, 
                          context: Dict[str, Any],
                          fallback_callback: Optional[Callable] = None) -> bool:
        """
        Handle error with appropriate recovery strategies.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            fallback_callback: Optional callback for fallback behavior
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        category, severity = self.classify_error(error, context)
        
        # Create error event
        error_event = ErrorEvent(
            timestamp=time.time(),
            error_type=type(error).__name__,
            category=category,
            severity=severity,
            message=str(error),
            stack_trace=traceback.format_exc(),
            context=context.copy()
        )
        
        # Add to history
        self.error_history.append(error_event)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)
        
        # Update statistics
        self.stats['total_errors'] += 1
        self.stats['errors_by_category'][category.value] += 1
        self.stats['errors_by_severity'][severity.value] += 1
        
        self._logger.error(f"Error occurred: {category.value}/{severity.value} - {error}")
        
        # Critical errors cannot be recovered
        if severity == ErrorSeverity.CRITICAL:
            self._logger.critical(f"Critical error, stopping processing: {error}")
            if fallback_callback:
                await fallback_callback(error, context)
            return False
        
        # Attempt recovery strategies
        recovery_successful = await self._attempt_recovery(error_event, context)
        
        if not recovery_successful and fallback_callback:
            self._logger.warning("All recovery attempts failed, invoking fallback")
            await fallback_callback(error, context)
        
        return recovery_successful
    
    async def _attempt_recovery(self, error_event: ErrorEvent, context: Dict[str, Any]) -> bool:
        """Attempt recovery using appropriate strategies."""
        strategies = self.strategies.get(error_event.category, [])
        
        if not strategies:
            self._logger.warning(f"No recovery strategies for category: {error_event.category}")
            return False
        
        error_event.recovery_attempted = True
        
        for strategy in strategies:
            if not strategy.can_attempt():
                self._logger.debug(f"Strategy {strategy.name} exhausted attempts")
                continue
            
            self.stats['recovery_attempts'] += 1
            
            try:
                # Create a mock exception from the error event for the strategy
                mock_error = Exception(error_event.message)
                success = await strategy.attempt_recovery(mock_error, context)
                
                if success:
                    self.stats['recovery_successes'] += 1
                    error_event.recovery_successful = True
                    self._logger.info(f"Recovery successful using strategy: {strategy.name}")
                    return True
                
            except Exception as recovery_error:
                self._logger.error(f"Recovery strategy {strategy.name} raised error: {recovery_error}")
        
        self._logger.warning(f"All recovery strategies failed for error: {error_event.error_type}")
        return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        recent_errors = [e for e in self.error_history if time.time() - e.timestamp < 3600]  # Last hour
        
        return {
            **self.stats,
            'recent_errors_count': len(recent_errors),
            'recovery_success_rate': (
                self.stats['recovery_successes'] / max(1, self.stats['recovery_attempts'])
            ),
            'error_frequency': len(self.error_history) / max(1, len(self.error_history)),
            'most_common_category': max(
                self.stats['errors_by_category'].items(),
                key=lambda x: x[1],
                default=('none', 0)
            )[0],
            'strategy_performance': {
                cat.value: {
                    'available_strategies': len(strategies),
                    'active_strategies': len([s for s in strategies if s.can_attempt()])
                }
                for cat, strategies in self.strategies.items()
            }
        }
    
    def reset_strategies(self, category: Optional[ErrorCategory] = None):
        """Reset recovery strategies for a category or all categories."""
        if category:
            for strategy in self.strategies.get(category, []):
                strategy.reset()
        else:
            for strategies in self.strategies.values():
                for strategy in strategies:
                    strategy.reset()


def error_recovery_decorator(recovery_manager: ErrorRecoveryManager,
                           context_provider: Optional[Callable] = None,
                           fallback_callback: Optional[Callable] = None):
    """
    Decorator to add error recovery to functions.
    
    Args:
        recovery_manager: The recovery manager to use
        context_provider: Optional function to provide context
        fallback_callback: Optional fallback function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = context_provider(*args, **kwargs) if context_provider else {}
                
                handled = await recovery_manager.handle_error(
                    e, context, fallback_callback
                )
                
                if not handled:
                    raise  # Re-raise if not handled
                
                # Try the function again with updated context
                if context.get('api_retry') or context.get('fallback_format'):
                    return await func(*args, **kwargs)
                
                return None  # Recovery changed behavior
        
        return wrapper
    return decorator