"""
Centralized Configuration Management
Uses Pydantic for validation and type safety
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration with validation"""
    
    # API Keys and Secrets
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY", description="OpenAI API key")
    supabase_url: str = Field(..., alias="SUPABASE_URL", description="Supabase project URL")
    supabase_anon_key: str = Field(..., alias="SUPABASE_ANON_KEY", description="Supabase anonymous key")
    supabase_service_key: Optional[str] = Field(None, alias="SUPABASE_SERVICE_KEY", description="Supabase service key")
    supabase_jwt_secret: Optional[str] = Field(None, alias="SUPABASE_JWT_SECRET", description="JWT secret for Supabase")
    
    # Google Cloud Configuration
    gcp_project_id: Optional[str] = Field(None, alias="GCP_PROJECT_ID", description="Google Cloud project ID")
    google_application_credentials: Optional[str] = Field(None, alias="GOOGLE_APPLICATION_CREDENTIALS", description="Path to GCP credentials")
    bigquery_dataset: Optional[str] = Field(None, alias="BIGQUERY_DATASET", description="BigQuery dataset name")
    
    # Application Settings
    app_env: str = Field("development", alias="APP_ENV", description="Application environment")
    port: int = Field(8080, alias="PORT", description="Server port")
    log_level: str = Field("INFO", alias="LOG_LEVEL", description="Logging level")
    debug: bool = Field(False, alias="DEBUG", description="Debug mode")
    
    # CORS Settings
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "https://rag-chatbot-20250806.web.app",
            "https://rag-chatbot-20250806.firebaseapp.com"
        ],
        alias="CORS_ORIGINS",
        description="Allowed CORS origins"
    )
    
    # File Upload Settings
    max_file_size: int = Field(30 * 1024 * 1024, alias="MAX_FILE_SIZE", description="Maximum file size in bytes")
    supported_file_extensions: List[str] = Field(
        default=[".pdf", ".txt", ".md", ".docx"],
        alias="SUPPORTED_EXTENSIONS",
        description="Supported file extensions"
    )
    
    # Feature Flags
    use_parallel_processing: bool = Field(True, alias="USE_PARALLEL_PROCESSING", description="Enable parallel processing")
    enable_bigquery: bool = Field(False, alias="ENABLE_BIGQUERY", description="Enable BigQuery integration")
    enable_auth: bool = Field(True, alias="ENABLE_AUTH", description="Enable authentication")
    
    # Performance Settings
    max_tokens: int = Field(800, alias="MAX_TOKENS", description="Maximum tokens for chat responses")  # 적절한 길이
    temperature: float = Field(0.7, alias="TEMPERATURE", description="Chat model temperature")  # 원래 설정
    chat_model: str = Field("gpt-4-1106-preview", alias="CHAT_MODEL", description="Chat model to use")  # GPT-4 유지
    use_threads: bool = Field(True, alias="USE_THREADS", description="Use Assistant API with Threads (False = Direct mode without threads)")
    
    # Assistant Configuration
    assistant_name: str = Field("청암 챗봇", alias="ASSISTANT_NAME", description="Assistant name")
    assistant_model: str = Field("gpt-4-turbo-preview", alias="ASSISTANT_MODEL", description="Assistant model")  # GPT-4 유지
    assistant_temperature: float = Field(0.7, alias="ASSISTANT_TEMPERATURE", description="Assistant temperature")
    assistant_max_tokens: int = Field(800, alias="ASSISTANT_MAX_TOKENS", description="Assistant max tokens")  # 적절한 길이
    
    # OpenAI Assistant and Vector Store IDs (from environment or fallback to JSON)
    openai_assistant_id: Optional[str] = Field(None, alias="OPENAI_ASSISTANT_ID", description="Persistent OpenAI Assistant ID")
    openai_vector_store_id: Optional[str] = Field(None, alias="OPENAI_VECTOR_STORE_ID", description="Persistent OpenAI Vector Store ID")
    assistant_config_path: str = Field("assistant_config.json", alias="ASSISTANT_CONFIG_PATH", description="Path to assistant config JSON (fallback)")
    
    # Cache Settings
    cache_ttl: int = Field(3600, alias="CACHE_TTL", description="Cache TTL in seconds")  # 1시간으로 증가
    enable_cache: bool = Field(True, alias="ENABLE_CACHE", description="Enable caching")
    
    # Database Settings
    database_pool_size: int = Field(10, alias="DATABASE_POOL_SIZE", description="Database connection pool size")
    database_max_overflow: int = Field(20, alias="DATABASE_MAX_OVERFLOW", description="Maximum overflow connections")
    
    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v):
        """Validate application environment"""
        valid_envs = ["development", "staging", "production", "test"]
        if v not in valid_envs:
            raise ValueError(f"app_env must be one of {valid_envs}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # If it's a string, split by comma
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("supported_file_extensions", mode="before")
    @classmethod
    def parse_file_extensions(cls, v):
        """Parse file extensions from string or list"""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @field_validator("google_application_credentials")
    @classmethod
    def validate_gcp_credentials(cls, v):
        """Validate GCP credentials file exists if provided"""
        if v and not Path(v).exists():
            # Log warning but don't fail - might be using default credentials
            import logging
            logging.warning(f"GCP credentials file not found: {v}")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.app_env == "development"
    
    def get_assistant_config(self) -> dict:
        """Get assistant configuration from env vars or fallback to JSON file"""
        import json
        
        # First try environment variables
        if self.openai_assistant_id and self.openai_vector_store_id:
            return {
                "assistant_id": self.openai_assistant_id,
                "vector_store_id": self.openai_vector_store_id
            }
        
        # Fallback to JSON file if it exists
        if Path(self.assistant_config_path).exists():
            with open(self.assistant_config_path, 'r') as f:
                config = json.load(f)
                return {
                    "assistant_id": config.get("assistant_id"),
                    "vector_store_id": config.get("vector_store_id")
                }
        
        # Return None if no configuration found
        return {
            "assistant_id": None,
            "vector_store_id": None
        }
    
    @property
    def bigquery_enabled(self) -> bool:
        """Check if BigQuery is properly configured"""
        return bool(
            self.enable_bigquery and 
            self.gcp_project_id and 
            self.bigquery_dataset
        )
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins list"""
        # Add dynamic localhost ports
        origins = list(self.cors_origins)
        for port in [3000, 3001, 3002, 5173, 8000, 8080]:
            origins.append(f"http://localhost:{port}")
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for origin in origins:
            if origin not in seen:
                seen.add(origin)
                result.append(origin)
        return result
    
    def get_supabase_headers(self) -> dict:
        """Get headers for Supabase requests"""
        headers = {
            "apikey": self.supabase_anon_key,
            "Authorization": f"Bearer {self.supabase_anon_key}"
        }
        if self.supabase_service_key:
            headers["Authorization"] = f"Bearer {self.supabase_service_key}"
        return headers
    
    def mask_secrets(self) -> dict:
        """Return configuration with masked secrets for logging"""
        config_dict = self.model_dump()  # Use model_dump() for Pydantic v2
        secret_fields = [
            "openai_api_key", 
            "supabase_anon_key", 
            "supabase_service_key",
            "supabase_jwt_secret"
        ]
        
        for field in secret_fields:
            if field in config_dict and config_dict[field]:
                # Keep first and last 4 characters
                value = str(config_dict[field])
                if len(value) > 8:
                    config_dict[field] = f"{value[:4]}...{value[-4:]}"
                else:
                    config_dict[field] = "***"
        
        return config_dict
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "populate_by_name": True  # Allow both field name and alias
    }


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
        
        # Log configuration (with secrets masked)
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Configuration loaded successfully")
        logger.debug(f"Configuration: {_settings.mask_secrets()}")
    
    return _settings


# Convenience function for backward compatibility
def get_env_var(key: str, default: str = None) -> str:
    """Get environment variable (backward compatibility)"""
    settings = get_settings()
    
    # Try to get from settings first
    if hasattr(settings, key.lower()):
        return str(getattr(settings, key.lower()))
    
    # Fall back to environment
    return os.getenv(key, default)