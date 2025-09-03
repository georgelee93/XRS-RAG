"""
Fallback Handler Module
Implements graceful degradation and fallback strategies for system failures
"""

import logging
import time
import json
from typing import Dict, Any, Optional, Callable, List, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from pathlib import Path

from .utils import get_env_var, create_error_response


logger = logging.getLogger(__name__)


class ServiceLevel(Enum):
    """Service degradation levels"""
    FULL_SERVICE = "full_service"
    REDUCED_SERVICE = "reduced_service"
    BASIC_SERVICE = "basic_service"
    MAINTENANCE_MODE = "maintenance_mode"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise ServiceUnavailableError(
                    f"Circuit breaker is OPEN. Service unavailable for {self._time_until_reset()}s"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (
            self.last_failure_time and 
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _time_until_reset(self) -> int:
        """Time remaining until circuit reset attempt"""
        if not self.last_failure_time:
            return 0
        
        elapsed = time.time() - self.last_failure_time
        return max(0, int(self.recovery_timeout - elapsed))
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class ServiceUnavailableError(Exception):
    """Raised when service is unavailable"""
    pass


class ResponseCache:
    """Cache for fallback responses"""
    
    def __init__(self, cache_dir: str = "./cache", ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl  # Time to live in seconds
        self.memory_cache = {}  # In-memory cache for fast access
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        # Check memory cache first
        if key in self.memory_cache:
            entry, timestamp = self.memory_cache[key]
            if time.time() - timestamp < self.ttl:
                return entry
            else:
                del self.memory_cache[key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                if time.time() - data["timestamp"] < self.ttl:
                    # Load into memory cache
                    self.memory_cache[key] = (data["response"], data["timestamp"])
                    return data["response"]
                else:
                    # Expired, remove file
                    cache_file.unlink()
            except Exception as e:
                logger.error(f"Error reading cache: {str(e)}")
        
        return None
    
    def set(self, key: str, response: Dict[str, Any]):
        """Cache a response"""
        timestamp = time.time()
        
        # Memory cache
        self.memory_cache[key] = (response, timestamp)
        
        # Disk cache
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    "response": response,
                    "timestamp": timestamp
                }, f)
        except Exception as e:
            logger.error(f"Error writing cache: {str(e)}")
    
    def clear_expired(self):
        """Remove expired cache entries"""
        current_time = time.time()
        
        # Clear memory cache
        expired_keys = [
            key for key, (_, timestamp) in self.memory_cache.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                if current_time - data["timestamp"] > self.ttl:
                    cache_file.unlink()
            except:
                # If we can't read it, remove it
                cache_file.unlink()


class FallbackHandler:
    """Main fallback handler that orchestrates degradation strategies"""
    
    def __init__(self):
        self.service_level = ServiceLevel.FULL_SERVICE
        self.cache = ResponseCache()
        
        # Circuit breakers for different services
        self.circuit_breakers = {
            "openai": CircuitBreaker(failure_threshold=3, recovery_timeout=60),
            "bigquery": CircuitBreaker(failure_threshold=5, recovery_timeout=30),
            "retrieval": CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        }
        
        # Fallback responses
        self.static_responses = self._load_static_responses()
    
    def _load_static_responses(self) -> Dict[str, str]:
        """Load predefined static responses"""
        return {
            "default": "I'm currently experiencing technical difficulties. Please try again in a few moments.",
            "rate_limit": "I've reached my usage limit. Please try again later.",
            "no_connection": "I'm unable to connect to my knowledge base. Please check your internet connection.",
            "maintenance": "The system is currently under maintenance. Please try again later.",
            
            # Common FAQs
            "greeting": "Hello! I'm an AI assistant. How can I help you today?",
            "help": "I can help you search through documents and answer questions based on available information.",
            "capabilities": "I can search documents, answer questions, and provide information from my knowledge base."
        }
    
    async def execute_with_fallback(self, primary_func: Callable, 
                                  fallback_funcs: List[Callable],
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute function with fallback chain"""
        # Try primary function
        try:
            service_name = context.get("service", "unknown")
            
            if service_name in self.circuit_breakers:
                circuit_breaker = self.circuit_breakers[service_name]
                result = await circuit_breaker.call(primary_func, context)
            else:
                result = await primary_func(context)
            
            # Cache successful response
            if context.get("cache_key"):
                self.cache.set(context["cache_key"], result)
            
            return result
            
        except Exception as e:
            logger.warning(f"Primary function failed: {str(e)}")
            
            # Try fallback functions
            for i, fallback in enumerate(fallback_funcs):
                try:
                    logger.info(f"Trying fallback {i + 1}")
                    result = await fallback(context)
                    
                    # Mark as fallback response
                    result["fallback_level"] = i + 1
                    result["degraded"] = True
                    
                    return result
                    
                except Exception as fallback_error:
                    logger.warning(f"Fallback {i + 1} failed: {str(fallback_error)}")
                    continue
            
            # All fallbacks failed, return final fallback
            return self._final_fallback_response(context)
    
    def _final_fallback_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ultimate fallback when everything fails"""
        query = context.get("query", "").lower()
        
        # Check for matching static response
        for key, response in self.static_responses.items():
            if key in query:
                return {
                    "status": "fallback",
                    "response": response,
                    "fallback_level": "static",
                    "degraded": True
                }
        
        # Default response
        return {
            "status": "fallback",
            "response": self.static_responses["default"],
            "fallback_level": "default",
            "degraded": True
        }
    
    async def check_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check if we have a cached response"""
        cached = self.cache.get(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached
        return None
    
    def update_service_level(self, level: ServiceLevel):
        """Update current service level"""
        self.service_level = level
        logger.info(f"Service level changed to: {level.value}")
    
    def get_service_capabilities(self) -> Dict[str, bool]:
        """Get current service capabilities based on level"""
        capabilities = {
            ServiceLevel.FULL_SERVICE: {
                "retrieval_api": True,
                "gpt4": True,
                "bigquery": True,
                "real_time": True,
                "advanced_search": True
            },
            ServiceLevel.REDUCED_SERVICE: {
                "retrieval_api": True,
                "gpt4": False,  # Use GPT-3.5 instead
                "bigquery": True,
                "real_time": False,  # Use cache
                "advanced_search": False
            },
            ServiceLevel.BASIC_SERVICE: {
                "retrieval_api": False,  # Use local cache
                "gpt4": False,
                "bigquery": False,
                "real_time": False,
                "advanced_search": False
            },
            ServiceLevel.MAINTENANCE_MODE: {
                "retrieval_api": False,
                "gpt4": False,
                "bigquery": False,
                "real_time": False,
                "advanced_search": False
            }
        }
        
        return capabilities.get(self.service_level, capabilities[ServiceLevel.MAINTENANCE_MODE])
    
    def get_fallback_message(self) -> str:
        """Get appropriate user message based on service level"""
        messages = {
            ServiceLevel.FULL_SERVICE: None,
            ServiceLevel.REDUCED_SERVICE: "Some features are currently limited. Response quality may be reduced.",
            ServiceLevel.BASIC_SERVICE: "Operating in basic mode. Only cached responses are available.",
            ServiceLevel.MAINTENANCE_MODE: "System is in maintenance mode. Limited functionality available."
        }
        
        return messages.get(self.service_level)


class LocalSearchFallback:
    """Local search implementation for when retrieval API is unavailable"""
    
    def __init__(self, index_path: str = "./local_index"):
        self.index_path = Path(index_path)
        self.index_path.mkdir(exist_ok=True)
        
        # Simple keyword index
        self.keyword_index = {}
        self.documents = {}
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Basic keyword search"""
        query_words = query.lower().split()
        scores = {}
        
        # Score documents based on keyword matches
        for doc_id, keywords in self.keyword_index.items():
            score = sum(1 for word in query_words if word in keywords)
            if score > 0:
                scores[doc_id] = score
        
        # Sort by score and return top results
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for doc_id, score in sorted_results:
            if doc_id in self.documents:
                results.append({
                    "document": self.documents[doc_id],
                    "score": score,
                    "method": "keyword_match"
                })
        
        return results
    
    def index_document(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """Index a document for local search"""
        # Extract keywords (simple tokenization)
        words = set(content.lower().split())
        
        self.keyword_index[doc_id] = words
        self.documents[doc_id] = {
            "content": content[:500],  # Store preview
            "metadata": metadata
        }