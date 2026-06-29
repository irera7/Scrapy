"""Smart retry system with intelligent backoff strategies."""
import asyncio
import random
from typing import TypeVar, Callable, Any, Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import structlog

logger = structlog.get_logger()

T = TypeVar('T')


class RetryStrategy(str, Enum):
    """Retry strategies."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    CONSTANT = "constant"
    ADAPTIVE = "adaptive"


class ErrorCategory(str, Enum):
    """Categories of errors for smart handling."""
    RATE_LIMIT = "rate_limit"           # 429, 503
    AUTH_ERROR = "auth_error"           # 401, 403
    NOT_FOUND = "not_found"             # 404
    SERVER_ERROR = "server_error"       # 500, 502, 503, 504
    NETWORK_ERROR = "network_error"     # Connection errors
    TIMEOUT = "timeout"                 # Request timeout
    CAPTCHA = "captcha"                 # CAPTCHA detected
    BLOCKED = "blocked"                 # IP blocked
    PARSE_ERROR = "parse_error"         # Content parsing failed
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # 5 minutes max
    jitter: bool = True  # Add randomness
    jitter_factor: float = 0.3
    
    # Per-error category settings
    error_delays: Dict[ErrorCategory, float] = field(default_factory=lambda: {
        ErrorCategory.RATE_LIMIT: 60.0,
        ErrorCategory.AUTH_ERROR: 0,  # Don't retry auth errors
        ErrorCategory.NOT_FOUND: 0,   # Don't retry 404s
        ErrorCategory.SERVER_ERROR: 30.0,
        ErrorCategory.NETWORK_ERROR: 5.0,
        ErrorCategory.TIMEOUT: 10.0,
        ErrorCategory.CAPTCHA: 30.0,
        ErrorCategory.BLOCKED: 300.0,
        ErrorCategory.PARSE_ERROR: 5.0,
        ErrorCategory.UNKNOWN: 10.0,
    })
    
    # Which errors should be retried
    retryable_errors: List[ErrorCategory] = field(default_factory=lambda: [
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.SERVER_ERROR,
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.TIMEOUT,
        ErrorCategory.CAPTCHA,
        ErrorCategory.PARSE_ERROR,
        ErrorCategory.UNKNOWN,
    ])


@dataclass
class RetryState:
    """State of retry attempts."""
    attempt: int = 0
    total_delay: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    last_error_category: Optional[ErrorCategory] = None
    successful: bool = False


class ErrorClassifier:
    """Classifies errors into categories."""
    
    @staticmethod
    def classify_http_status(status_code: int) -> ErrorCategory:
        """Classify HTTP status code."""
        if status_code == 429:
            return ErrorCategory.RATE_LIMIT
        elif status_code in [401, 403]:
            return ErrorCategory.AUTH_ERROR
        elif status_code == 404:
            return ErrorCategory.NOT_FOUND
        elif status_code in [500, 502, 503, 504]:
            return ErrorCategory.SERVER_ERROR
        elif status_code >= 400:
            return ErrorCategory.UNKNOWN
        return ErrorCategory.UNKNOWN
    
    @staticmethod
    def classify_exception(error: Exception) -> ErrorCategory:
        """Classify Python exception."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Network errors
        if any(t in error_type for t in ['ConnectionError', 'ConnectError', 'SSLError']):
            return ErrorCategory.NETWORK_ERROR
        
        # Timeout
        if 'Timeout' in error_type or 'timeout' in error_msg:
            return ErrorCategory.TIMEOUT
        
        # CAPTCHA detection
        if 'captcha' in error_msg or 'challenge' in error_msg:
            return ErrorCategory.CAPTCHA
        
        # Blocked
        if any(w in error_msg for w in ['blocked', 'banned', 'forbidden', 'access denied']):
            return ErrorCategory.BLOCKED
        
        # Rate limiting
        if any(w in error_msg for w in ['rate limit', 'too many requests', 'throttle']):
            return ErrorCategory.RATE_LIMIT
        
        # Parse errors
        if any(t in error_type for t in ['JSONDecodeError', 'ParseError', 'XMLSyntaxError']):
            return ErrorCategory.PARSE_ERROR
        
        return ErrorCategory.UNKNOWN
    
    @staticmethod
    def classify_response_content(content: str) -> Optional[ErrorCategory]:
        """Classify based on response content."""
        content_lower = content.lower()
        
        if any(w in content_lower for w in ['captcha', 'recaptcha', 'hcaptcha', 'verify you are human']):
            return ErrorCategory.CAPTCHA
        
        if any(w in content_lower for w in ['access denied', 'forbidden', 'blocked', 'banned']):
            return ErrorCategory.BLOCKED
        
        if any(w in content_lower for w in ['rate limit', 'too many requests', 'slow down']):
            return ErrorCategory.RATE_LIMIT
        
        return None


class DelayCalculator:
    """Calculates delay between retries."""
    
    @staticmethod
    def exponential(attempt: int, base_delay: float, max_delay: float) -> float:
        """Exponential backoff: delay = base * 2^attempt."""
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)
    
    @staticmethod
    def linear(attempt: int, base_delay: float, max_delay: float) -> float:
        """Linear backoff: delay = base * attempt."""
        delay = base_delay * (attempt + 1)
        return min(delay, max_delay)
    
    @staticmethod
    def fibonacci(attempt: int, base_delay: float, max_delay: float) -> float:
        """Fibonacci backoff."""
        def fib(n):
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            return a
        
        delay = base_delay * fib(attempt + 2)
        return min(delay, max_delay)
    
    @staticmethod
    def constant(attempt: int, base_delay: float, max_delay: float) -> float:
        """Constant delay."""
        return base_delay
    
    @staticmethod
    def add_jitter(delay: float, factor: float = 0.3) -> float:
        """Add random jitter to delay."""
        jitter = delay * factor
        return delay + random.uniform(-jitter, jitter)


class SmartRetry:
    """Smart retry handler with adaptive strategies."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.classifier = ErrorClassifier()
        
        # Track per-domain error history for adaptive retries
        self._domain_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def calculate_delay(
        self,
        attempt: int,
        error_category: Optional[ErrorCategory] = None
    ) -> float:
        """Calculate delay for next retry."""
        
        # Check for category-specific delay
        if error_category and error_category in self.config.error_delays:
            base = self.config.error_delays[error_category]
            if base == 0:
                return 0  # Don't retry
        else:
            base = self.config.base_delay
        
        # Calculate based on strategy
        if self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = DelayCalculator.exponential(attempt, base, self.config.max_delay)
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = DelayCalculator.linear(attempt, base, self.config.max_delay)
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = DelayCalculator.fibonacci(attempt, base, self.config.max_delay)
        elif self.config.strategy == RetryStrategy.CONSTANT:
            delay = DelayCalculator.constant(attempt, base, self.config.max_delay)
        elif self.config.strategy == RetryStrategy.ADAPTIVE:
            delay = self._adaptive_delay(attempt, error_category)
        else:
            delay = base
        
        # Add jitter
        if self.config.jitter:
            delay = DelayCalculator.add_jitter(delay, self.config.jitter_factor)
        
        return max(0, delay)
    
    def _adaptive_delay(
        self,
        attempt: int,
        error_category: Optional[ErrorCategory]
    ) -> float:
        """Adaptive delay based on error history."""
        base = self.config.base_delay
        
        # Start with exponential
        delay = DelayCalculator.exponential(attempt, base, self.config.max_delay)
        
        # Adjust based on error category
        if error_category == ErrorCategory.RATE_LIMIT:
            delay = max(delay, 60.0)  # At least 1 minute for rate limits
        elif error_category == ErrorCategory.BLOCKED:
            delay = max(delay, 300.0)  # 5 minutes for blocks
        elif error_category == ErrorCategory.SERVER_ERROR:
            delay = max(delay, 30.0)  # 30 seconds for server errors
        
        return delay
    
    def should_retry(
        self,
        state: RetryState,
        error_category: ErrorCategory
    ) -> bool:
        """Determine if we should retry."""
        # Check max retries
        if state.attempt >= self.config.max_retries:
            return False
        
        # Check if error category is retryable
        if error_category not in self.config.retryable_errors:
            return False
        
        # Check for specific non-retryable cases
        if error_category in [ErrorCategory.AUTH_ERROR, ErrorCategory.NOT_FOUND]:
            return False
        
        return True
    
    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        on_retry: Optional[Callable[[RetryState], None]] = None,
        on_error: Optional[Callable[[Exception, ErrorCategory], None]] = None,
        **kwargs
    ) -> T:
        """Execute a function with smart retry logic."""
        state = RetryState()
        
        while True:
            try:
                result = await func(*args, **kwargs)
                state.successful = True
                return result
            
            except Exception as e:
                # Classify error
                error_category = self.classifier.classify_exception(e)
                state.last_error_category = error_category
                
                # Record error
                state.errors.append({
                    "attempt": state.attempt,
                    "error": str(e),
                    "category": error_category.value,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Callback for error
                if on_error:
                    on_error(e, error_category)
                
                # Check if we should retry
                if not self.should_retry(state, error_category):
                    logger.error(
                        f"Not retrying after {state.attempt + 1} attempts",
                        error=str(e),
                        category=error_category.value
                    )
                    raise
                
                # Calculate delay
                delay = self.calculate_delay(state.attempt, error_category)
                
                if delay == 0:
                    raise
                
                state.attempt += 1
                state.total_delay += delay
                
                logger.warning(
                    f"Retry {state.attempt}/{self.config.max_retries}",
                    error=str(e),
                    category=error_category.value,
                    delay=f"{delay:.1f}s"
                )
                
                # Callback for retry
                if on_retry:
                    on_retry(state)
                
                # Wait before retry
                await asyncio.sleep(delay)


def with_retry(
    max_retries: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 300.0
):
    """Decorator for adding retry logic to async functions."""
    config = RetryConfig(
        max_retries=max_retries,
        strategy=strategy,
        base_delay=base_delay,
        max_delay=max_delay
    )
    retry_handler = SmartRetry(config)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascade failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = "closed"  # closed, open, half-open
        self._half_open_calls = 0
    
    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == "open":
            # Check if we should transition to half-open
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.reset_timeout:
                    self._state = "half-open"
                    self._half_open_calls = 0
        
        return self._state
    
    def record_success(self):
        """Record a successful call."""
        if self._state == "half-open":
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = "closed"
                self._failure_count = 0
        else:
            self._failure_count = 0
    
    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._state == "half-open":
            self._state = "open"
        elif self._failure_count >= self.failure_threshold:
            self._state = "open"
    
    def can_execute(self) -> bool:
        """Check if calls are allowed."""
        state = self.state
        return state in ["closed", "half-open"]
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute function with circuit breaker."""
        if not self.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is open. Reset in {self.reset_timeout - (datetime.now() - self._last_failure_time).total_seconds():.1f}s"
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Global instances for different use cases
default_retry = SmartRetry()
aggressive_retry = SmartRetry(RetryConfig(
    max_retries=5,
    strategy=RetryStrategy.FIBONACCI,
    base_delay=2.0,
    max_delay=600.0
))
conservative_retry = SmartRetry(RetryConfig(
    max_retries=2,
    strategy=RetryStrategy.CONSTANT,
    base_delay=5.0,
    max_delay=30.0
))

