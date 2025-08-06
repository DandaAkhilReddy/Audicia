"""
AUDICIA VOICE-TO-SOAP SYSTEM
Production Configuration Management
All secrets loaded from environment variables
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Production configuration dictionary
CONFIG = {
    "POSTGRES": {
        "HOST": os.getenv("POSTGRES_SERVER"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "DATABASE": os.getenv("POSTGRES_DB"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "URL": os.getenv("DATABASE_URL")
    },
    "AZURE_SPEECH": {
        "KEY": os.getenv("AZURE_SPEECH_KEY"),
        "ENDPOINT": os.getenv("AZURE_SPEECH_ENDPOINT"),
        "REGION": os.getenv("AZURE_SPEECH_REGION"),
    },
    "OPENAI": {
        "API_KEY": os.getenv("OPENAI_API_KEY"),
        "MODEL": "gpt-4-turbo-preview",
        "TEMPERATURE": 0.1,
        "MAX_TOKENS": 3000
    },
    "AZURE_STORAGE": {
        "ACCOUNT_NAME": os.getenv("AZURE_STORAGE_ACCOUNT_NAME"),
        "ACCOUNT_KEY": os.getenv("AZURE_STORAGE_ACCOUNT_KEY"),
        "CONTAINER_NAME": os.getenv("AZURE_BLOB_CONTAINER_NAME"),
    },
    "KEY_VAULT": {
        "NAME": os.getenv("AZURE_KEY_VAULT_NAME"),
    },
    "SECURITY": {
        "JWT_SECRET": os.getenv("JWT_SECRET_KEY"),
        "ENCRYPTION_KEY": os.getenv("PHI_ENCRYPTION_KEY"),
    },
    "APPLICATION": {
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
        "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
        "HOST": os.getenv("API_HOST", "0.0.0.0"),
        "PORT": int(os.getenv("API_PORT", "8000")),
        "REGION": os.getenv("AZURE_REGION", "eastus"),
        "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    }
}

# Helper functions for easy access
def get_database_url() -> str:
    """Get PostgreSQL database URL"""
    return CONFIG["POSTGRES"]["URL"]

def get_azure_speech_config() -> Dict[str, str]:
    """Get Azure Speech Service configuration"""
    return CONFIG["AZURE_SPEECH"]

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration"""
    return CONFIG["OPENAI"]

def get_security_config() -> Dict[str, str]:
    """Get security configuration"""
    return CONFIG["SECURITY"]

def is_production() -> bool:
    """Check if running in production environment"""
    return CONFIG["APPLICATION"]["ENVIRONMENT"] == "production"

def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return CONFIG["APPLICATION"]["DEBUG"]

# Validation function
def validate_config() -> bool:
    """Validate that all required configuration is present"""
    required_keys = [
        ("POSTGRES", "HOST"),
        ("POSTGRES", "USER"), 
        ("POSTGRES", "PASSWORD"),
        ("AZURE_SPEECH", "KEY"),
        ("AZURE_SPEECH", "REGION"),
        ("OPENAI", "API_KEY")
    ]
    
    missing_keys = []
    for section, key in required_keys:
        if not CONFIG.get(section, {}).get(key):
            missing_keys.append(f"{section}.{key}")
    
    if missing_keys:
        print(f"❌ Missing required configuration keys: {', '.join(missing_keys)}")
        return False
    
    print("✅ All required configuration keys are present")
    return True

if __name__ == "__main__":
    # Test configuration loading
    print("Testing configuration loading...")
    
    if validate_config():
        print("\n📊 Configuration Summary:")
        print(f"Environment: {CONFIG['APPLICATION']['ENVIRONMENT']}")
        print(f"Database: {CONFIG['POSTGRES']['HOST']}")
        print(f"Speech Region: {CONFIG['AZURE_SPEECH']['REGION']}")
        print(f"OpenAI Model: {CONFIG['OPENAI']['MODEL']}")
        print(f"Key Vault: {CONFIG['KEY_VAULT']['NAME']}")
        print("\n🚀 Configuration is ready for production!")
    else:
        print("\n❌ Configuration validation failed!")