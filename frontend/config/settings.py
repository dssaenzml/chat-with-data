from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class FrontendSettings(BaseSettings):
    """Frontend application settings"""
    
    # Application
    app_name: str = "Chat with Data Frontend"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Streamlit Configuration
    streamlit_host: str = "0.0.0.0"
    streamlit_port: int = 3000
    streamlit_theme: str = "light"
    
    # Backend API Configuration
    backend_url: Optional[str] = None
    api_timeout: int = 30
    api_retries: int = 3
    
    # File Upload Configuration
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = ["csv", "xlsx", "xls", "json", "parquet"]
    
    # UI Configuration
    enable_chat_history: bool = True
    enable_data_visualization: bool = True
    enable_file_upload: bool = True
    enable_database_connection: bool = True
    
    # Chat Configuration
    default_session_timeout: int = 3600  # 1 hour
    max_chat_history: int = 100
    enable_message_timestamps: bool = True
    
    # Visualization Configuration
    default_chart_theme: str = "plotly"
    chart_color_scheme: str = "viridis"
    enable_interactive_charts: bool = True
    
    # Security Configuration
    enable_auth: bool = False
    auth_provider: str = "local"  # local, oauth, saml
    session_secret: str = "your-secret-key-here-change-in-production"
    
    # Feature Flags
    enable_advanced_analytics: bool = True
    enable_sql_queries: bool = True
    enable_data_export: bool = True
    enable_multi_file_upload: bool = True
    
    def get_backend_url(self) -> str:
        """Get backend URL from environment"""
        return os.getenv("BACKEND_ENDPOINT", "http://chat-backend.orb.local:8000")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
_frontend_settings: Optional[FrontendSettings] = None

def get_frontend_settings() -> FrontendSettings:
    """Get frontend settings singleton"""
    global _frontend_settings
    if _frontend_settings is None:
        _frontend_settings = FrontendSettings()
    return _frontend_settings

# Environment-specific configurations
class DevelopmentFrontendSettings(FrontendSettings):
    """Development environment settings"""
    debug: bool = True
    streamlit_theme: str = "light"

class ProductionFrontendSettings(FrontendSettings):
    """Production environment settings"""
    debug: bool = False
    enable_auth: bool = True
    
class TestingFrontendSettings(FrontendSettings):
    """Testing environment settings"""
    debug: bool = True
    backend_url: str = "http://localhost:8001"  # Test backend

def get_environment_frontend_settings() -> FrontendSettings:
    """Get environment-specific frontend settings"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionFrontendSettings()
    elif env == "testing":
        return TestingFrontendSettings()
    else:
        return DevelopmentFrontendSettings() 