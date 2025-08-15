import logging
import pybreaker
from .config import settings

# Configureer een logger specifiek voor de circuit breaker
breaker_logger = logging.getLogger("pybreaker")


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Logt de statusveranderingen van de Circuit Breaker."""

    def state_change(self, cb, old_state, new_state):
        breaker_logger.warning(f"🔴 CRITICAL: CircuitBreaker state change: {old_state} → {new_state}")
        breaker_logger.warning(f"🔴 Circuit breaker details: fail_counter={cb.fail_counter}, fail_max={cb.fail_max}, reset_timeout={cb.reset_timeout}s")
        
        if new_state == 'open':
            breaker_logger.error(f"🚨 CIRCUIT BREAKER OPENED - All subsequent API calls will be BLOCKED for {cb.reset_timeout} seconds!")
        elif new_state == 'closed':
            breaker_logger.info(f"✅ Circuit breaker CLOSED - API calls will proceed normally")
        elif new_state == 'half-open':
            breaker_logger.info(f"🟡 Circuit breaker HALF-OPEN - Testing if service has recovered")
    
    def failure(self, cb, exc):
        breaker_logger.error(f"❌ Circuit breaker recorded FAILURE #{cb.fail_counter}/{cb.fail_max}: {exc}")
        if cb.fail_counter >= cb.fail_max - 1:
            breaker_logger.warning(f"⚠️  WARNING: Circuit breaker approaching threshold! Next failure will OPEN the circuit.")
    
    def success(self, cb):
        breaker_logger.info(f"✅ Circuit breaker recorded SUCCESS - fail_counter reset to 0")


# Maak een globale Circuit Breaker-instantie
circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=settings.CIRCUIT_BREAKER_FAIL_MAX,
    reset_timeout=settings.CIRCUIT_BREAKER_RESET_TIMEOUT_S,
    listeners=[CircuitBreakerListener()],
)

# Log initial circuit breaker configuration
breaker_logger.info(f"Circuit breaker initialized: fail_max={settings.CIRCUIT_BREAKER_FAIL_MAX}, reset_timeout={settings.CIRCUIT_BREAKER_RESET_TIMEOUT_S}s")
breaker_logger.info(f"Circuit breaker initial state: {circuit_breaker.current_state}")