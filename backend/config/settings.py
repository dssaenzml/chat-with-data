from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Chat with Data API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Database Configuration - Support for different deployment modes
    mongodb_url: Optional[str] = None
    mongodb_database: str = "chatdb"
    
    # Vector Database Configuration
    qdrant_url: Optional[str] = None
    qdrant_collection_name: str = "chat_vectors"
    qdrant_vector_size: int = 384
    
    # Redis Configuration
    redis_url: Optional[str] = None
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # PostgreSQL Configuration
    postgres_url: Optional[str] = None
    
    # MinIO Configuration
    minio_endpoint: Optional[str] = None
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_secure: bool = False
    
    # AI/LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # LangChain Configuration
    langchain_tracing_v2: bool = False
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: Optional[str] = None
    langchain_project: str = "chat-with-data"
    
    # Langfuse Configuration (LLM Observability)
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: Optional[str] = None
    langfuse_enabled: bool = False
    langfuse_debug: bool = False
    langfuse_flush_at: int = 15  # Number of events to flush
    langfuse_flush_interval: float = 0.5  # Seconds between flushes
    langfuse_max_retries: int = 3
    
    # CrewAI Configuration
    crewai_model: str = "gpt-4"
    crewai_temperature: float = 0.7
    crewai_max_tokens: int = 2000
    
    # File Upload Configuration
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = ["csv", "xlsx", "xls", "json", "parquet"]
    upload_directory: str = "/app/uploads"
    
    # Security Configuration
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS Configuration
    allowed_origins: List[str] = ["*"]
    allowed_methods: List[str] = ["*"]
    allowed_headers: List[str] = ["*"]
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Caching
    cache_ttl: int = 300  # 5 minutes
    cache_enabled: bool = True
    
    # Background Tasks
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Feature Flags
    enable_websockets: bool = True
    enable_file_upload: bool = True
    enable_database_connections: bool = True
    enable_vector_search: bool = True
    enable_langgraph: bool = True
    
    def get_mongodb_url(self) -> str:
        """Get MongoDB URL from environment"""
        return os.getenv("MONGODB_ENDPOINT", "mongodb://admin:password123@chat-mongodb.orb.local:27017/chatdb?authSource=admin")
    
    def get_qdrant_url(self) -> str:
        """Get Qdrant URL from environment"""
        return os.getenv("QDRANT_ENDPOINT", "http://chat-qdrant.orb.local:6333")
    
    def get_redis_url(self) -> str:
        """Get Redis URL from environment"""
        return os.getenv("REDIS_ENDPOINT", "redis://chat-redis.orb.local:6379")
    
    def get_postgres_url(self) -> str:
        """Get PostgreSQL URL from environment"""
        return os.getenv("POSTGRES_ENDPOINT", "postgresql://postgres:postgres123@chat-postgres.orb.local:5432/sampledb")
    
    def get_minio_endpoint(self) -> str:
        """Get MinIO endpoint from environment"""
        return os.getenv("MINIO_ENDPOINT", "chat-minio.orb.local:9000")
    
    def get_langfuse_host(self) -> str:
        """Get Langfuse host URL from environment"""
        return os.getenv("LANGFUSE_ENDPOINT", "http://chat-langfuse.orb.local:3001")
    
    def get_celery_urls(self) -> tuple[str, str]:
        """Get Celery broker and result backend URLs"""
        redis_url = self.get_redis_url()
        broker_url = self.celery_broker_url or f"{redis_url}/0"
        result_backend = self.celery_result_backend or f"{redis_url}/0"
        return broker_url, result_backend

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    api_reload: bool = True

class ProductionSettings(Settings):
    """Production environment settings"""
    debug: bool = False
    log_level: str = "WARNING"
    api_reload: bool = False
    allowed_origins: List[str] = ["https://yourdomain.com"]

class TestingSettings(Settings):
    """Testing environment settings"""
    debug: bool = True
    mongodb_database: str = "chatdb_test"
    qdrant_collection_name: str = "test_vectors"

def get_environment_settings() -> Settings:
    """Get environment-specific settings"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings() 