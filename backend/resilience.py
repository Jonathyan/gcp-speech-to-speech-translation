import logging
import pybreaker
from .config import settings

# Configureer een logger specifiek voor de circuit breaker
breaker_logger = logging.getLogger("pybreaker")


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """Logt de statusveranderingen van de Circuit Breaker."""

    def state_change(self, cb, old_state, new_state):
        breaker_logger.warning(f"CircuitBreaker state change: from {old_state} to {new_state}")


# Maak een globale Circuit Breaker-instantie
circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=settings.CIRCUIT_BREAKER_FAIL_MAX,
    reset_timeout=settings.CIRCUIT_BREAKER_RESET_TIMEOUT_S,
    listeners=[CircuitBreakerListener()],
)