"""
QA Test Configuration
Supports both local and deployed testing
"""
import os
from typing import Optional
from enum import Enum

class TestEnvironment(Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"

class QAConfig:
    """Configuration for QA tests that can target different environments"""
    
    def __init__(self, environment: str = None):
        """
        Initialize QA configuration
        
        Args:
            environment: 'local', 'staging', or 'production'
                        If not provided, uses QA_ENV environment variable
                        Defaults to 'local' if neither is set
        """
        # Determine environment
        env = environment or os.getenv("QA_ENV", "local")
        self.environment = TestEnvironment(env.lower())
        
        # Set URLs based on environment
        self._set_urls()
        
        # Load authentication if needed
        self._load_auth()
        
    def _set_urls(self):
        """Set backend and frontend URLs based on environment"""
        
        if self.environment == TestEnvironment.LOCAL:
            self.backend_url = os.getenv("QA_BACKEND_URL", "http://localhost:8080")
            self.frontend_url = os.getenv("QA_FRONTEND_URL", "http://localhost:3000")
            
        elif self.environment == TestEnvironment.STAGING:
            # Staging URLs (example - replace with actual)
            self.backend_url = os.getenv("QA_BACKEND_URL", "https://rag-backend-staging.run.app")
            self.frontend_url = os.getenv("QA_FRONTEND_URL", "https://rag-chatbot-staging.web.app")
            
        elif self.environment == TestEnvironment.PRODUCTION:
            # Production URLs (Seoul region)
            self.backend_url = os.getenv("QA_BACKEND_URL", "https://rag-backend-223940753124.asia-northeast3.run.app")
            self.frontend_url = os.getenv("QA_FRONTEND_URL", "https://rag-chatbot-20250806.web.app")
            
        else:
            raise ValueError(f"Unknown environment: {self.environment}")
            
    def _load_auth(self):
        """Load authentication tokens/headers if needed"""
        self.auth_token = os.getenv("QA_AUTH_TOKEN")
        self.api_key = os.getenv("QA_API_KEY")
        
        # Build auth headers
        self.auth_headers = {}
        if self.auth_token:
            self.auth_headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.api_key:
            self.auth_headers["X-API-Key"] = self.api_key
            
    def get_headers(self, additional_headers: dict = None) -> dict:
        """Get headers for requests including auth"""
        headers = self.auth_headers.copy()
        if additional_headers:
            headers.update(additional_headers)
        return headers
        
    def is_local(self) -> bool:
        """Check if testing local environment"""
        return self.environment == TestEnvironment.LOCAL
        
    def is_deployed(self) -> bool:
        """Check if testing deployed environment"""
        return self.environment in [TestEnvironment.STAGING, TestEnvironment.PRODUCTION]
        
    def __str__(self) -> str:
        return f"""
QA Configuration:
  Environment: {self.environment.value}
  Backend URL: {self.backend_url}
  Frontend URL: {self.frontend_url}
  Auth Configured: {bool(self.auth_headers)}
"""

# Singleton instance
_config: Optional[QAConfig] = None

def get_qa_config(environment: str = None) -> QAConfig:
    """Get or create QA configuration singleton"""
    global _config
    if _config is None or environment:
        _config = QAConfig(environment)
    return _config