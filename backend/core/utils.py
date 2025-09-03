"""
Utility functions for the RAG project
"""

import os
import json
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


def get_env_var(key: str, default: Optional[str] = None, required: bool = True) -> Optional[str]:
    """Get environment variable with optional default - bridges to new config system"""
    # Try to use the new configuration system first
    try:
        from core.config import get_settings
        settings = get_settings()
        
        # Map common environment variables to settings attributes
        key_mapping = {
            "OPENAI_API_KEY": "openai_api_key",
            "SUPABASE_URL": "supabase_url",
            "SUPABASE_ANON_KEY": "supabase_anon_key",
            "SUPABASE_SERVICE_KEY": "supabase_service_key",
            "SUPABASE_JWT_SECRET": "supabase_jwt_secret",
            "GCP_PROJECT_ID": "gcp_project_id",
            "GOOGLE_APPLICATION_CREDENTIALS": "google_application_credentials",
            "BIGQUERY_DATASET": "bigquery_dataset",
            "APP_ENV": "app_env",
            "PORT": "port",
            "LOG_LEVEL": "log_level",
            "DEBUG": "debug",
            "MAX_FILE_SIZE": "max_file_size",
            "USE_PARALLEL_PROCESSING": "use_parallel_processing",
            "ENABLE_BIGQUERY": "enable_bigquery",
            "ENABLE_AUTH": "enable_auth",
            "MAX_TOKENS": "max_tokens",
            "TEMPERATURE": "temperature",
            "CHAT_MODEL": "chat_model",
            "CACHE_TTL": "cache_ttl",
            "ENABLE_CACHE": "enable_cache",
        }
        
        # Check if we have a mapping for this key
        if key in key_mapping:
            attr_name = key_mapping[key]
            if hasattr(settings, attr_name):
                value = getattr(settings, attr_name)
                # Convert to string if needed
                if value is not None:
                    return str(value)
    except Exception as e:
        # If config system fails, fall back to direct env var
        logger.debug(f"Config system not available, falling back to environment: {e}")
    
    # Fall back to direct environment variable access
    from pathlib import Path
    from dotenv import load_dotenv
    
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    value = os.getenv(key, default)
    
    # In production (Cloud Run), be more lenient with missing env vars during import
    if required and value is None:
        # Check if we're in Cloud Run environment
        if os.getenv("K_SERVICE") or os.getenv("K_REVISION"):
            logger.warning(f"Environment variable '{key}' is not set in Cloud Run, using default")
            return default
        else:
            raise ValueError(f"Environment variable '{key}' is required but not set")
    return value


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Configure logging for the application"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )


def calculate_cost(tokens: Union[int, Any], model: str = "gpt-4") -> float:
    """Calculate API cost based on token usage
    
    Args:
        tokens: Either an integer of total tokens or a CompletionUsage object
        model: The model name for pricing
    """
    # Pricing as of 2024 (subject to change)
    pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4-1106-preview": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    }
    
    if model not in pricing:
        logger.warning(f"Unknown model {model}, using gpt-4 pricing")
        model = "gpt-4"
    
    # Handle CompletionUsage object
    if hasattr(tokens, 'prompt_tokens') and hasattr(tokens, 'completion_tokens'):
        # Calculate actual cost based on prompt and completion tokens
        input_cost = (tokens.prompt_tokens / 1000) * pricing[model]["input"]
        output_cost = (tokens.completion_tokens / 1000) * pricing[model]["output"]
        cost = input_cost + output_cost
    else:
        # Handle integer tokens with 50/50 split estimation
        total_tokens = int(tokens) if not isinstance(tokens, int) else tokens
        avg_price = (pricing[model]["input"] + pricing[model]["output"]) / 2
        cost = (total_tokens / 1000) * avg_price
    
    return round(cost, 4)


def hash_content(content: str) -> str:
    """Generate SHA256 hash of content"""
    return hashlib.sha256(content.encode()).hexdigest()


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file"""
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(path, 'r') as f:
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif path.suffix == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def extract_file_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from a file"""
    import mimetypes
    
    path = Path(file_path)
    stat = path.stat()
    
    # Get MIME type
    content_type, _ = mimetypes.guess_type(str(path))
    if not content_type:
        # Default types for common extensions
        ext_to_mime = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.json': 'application/json',
            '.xml': 'text/xml',
            '.html': 'text/html',
            '.csv': 'text/csv'
        }
        content_type = ext_to_mime.get(path.suffix.lower(), 'application/octet-stream')
    
    return {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "path": str(path.absolute()),
        "content_type": content_type
    }


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks
    Note: OpenAI Retrieval API handles chunking automatically,
    but this is useful for local processing or analysis
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    import unicodedata
    
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    
    # Keep only ASCII alphanumeric, dots, dashes, underscores, and spaces
    # This will remove Korean and other non-ASCII characters
    filename = re.sub(r'[^\w\s.-]', '_', filename, flags=re.ASCII)
    
    # Replace multiple underscores with single underscore
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing spaces, dots, and underscores
    filename = filename.strip('. _')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    # Limit length to avoid issues
    name_part, ext = os.path.splitext(filename)
    if len(name_part) > 100:
        name_part = name_part[:100]
    filename = name_part + ext
    
    return filename


def create_error_response(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        "status": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.now().isoformat()
    }
    
    if context:
        response["context"] = context
    
    return response


def retry_with_backoff(func, max_attempts: int = 3, initial_delay: float = 1.0):
    """
    Retry a function with exponential backoff
    Used as a simple alternative to tenacity for basic cases
    """
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            import time
            time.sleep(delay)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(timestamp: Union[int, float, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to string"""
    if isinstance(timestamp, (int, float)):
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        raise ValueError(f"Invalid timestamp type: {type(timestamp)}")
    
    return dt.strftime(format_str)


def parse_file_type(filename: str) -> str:
    """Determine file type from filename"""
    ext = Path(filename).suffix.lower()
    
    file_types = {
        ".pdf": "pdf",
        ".doc": "word",
        ".docx": "word",
        ".txt": "text",
        ".md": "markdown",
        ".ppt": "powerpoint",
        ".pptx": "powerpoint",
        ".xls": "excel",
        ".xlsx": "excel",
        ".csv": "csv",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".htm": "html"
    }
    
    return file_types.get(ext, "unknown")


def validate_api_key(api_key: str, prefix: str = "sk-") -> bool:
    """Basic validation of API key format"""
    if not api_key:
        return False
    
    # Check if it starts with expected prefix
    if not api_key.startswith(prefix):
        return False
    
    # Check minimum length
    if len(api_key) < 20:
        return False
    
    return True


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result