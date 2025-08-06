"""
AUDICIA VOICE-TO-SOAP SYSTEM
Simple Secret Manager with Environment Variable Support
Direct access to your provided configuration
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger()

# Load environment variables from .env file
load_dotenv()

class SimpleSecretManager:
    """
    Simple secret manager that works with environment variables
    Falls back to hardcoded values for immediate testing
    """
    
    def __init__(self):
        self.secrets = {
            # Database configuration
            "PG_HOST": os.getenv("POSTGRES_SERVER"),
            "PG_USERNAME": os.getenv("POSTGRES_USER"), 
            "PG_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "PG_DATABASE": os.getenv("POSTGRES_DB"),
            "PG_PORT": os.getenv("POSTGRES_PORT", "5432"),
            
            # Azure Speech Service
            "AZURE_SPEECH_KEY": os.getenv("AZURE_SPEECH_KEY"),
            "AZURE_SPEECH_REGION": os.getenv("AZURE_SPEECH_REGION"),
            
            # OpenAI
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            
            # Security keys
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY"),
            "PHI_ENCRYPTION_KEY": os.getenv("PHI_ENCRYPTION_KEY")
        }
        
        logger.info("Simple secret manager initialized successfully")
    
    def get_secret(self, secret_name: str) -> str:
        """Get secret value by name"""
        value = self.secrets.get(secret_name)
        if not value:
            raise RuntimeError(f"Secret '{secret_name}' not found")
        
        logger.debug("Retrieved secret", secret_name=secret_name, has_value=bool(value))
        return value
    
    def get_multiple_secrets(self, secret_names: list) -> Dict[str, str]:
        """Get multiple secrets at once"""
        result = {}
        for name in secret_names:
            try:
                result[name] = self.get_secret(name)
            except RuntimeError:
                logger.warning("Missing secret", secret_name=name)
        return result
    
    def validate_required_secrets(self, required_secrets: list) -> bool:
        """Validate all required secrets are present"""
        missing = []
        for secret_name in required_secrets:
            if not self.secrets.get(secret_name):
                missing.append(secret_name)
        
        if missing:
            logger.error("Missing required secrets", missing_secrets=missing)
            return False
        
        logger.info("All required secrets validated")
        return True

# Global instance
secret_manager = SimpleSecretManager()

# Convenience functions that match the original interface
def get_secret(secret_name: str) -> str:
    """Get a single secret value"""
    return secret_manager.get_secret(secret_name)

def get_database_config() -> Dict[str, str]:
    """Get all database configuration secrets"""
    return secret_manager.get_multiple_secrets([
        "PG_HOST", "PG_PORT", "PG_USERNAME", "PG_PASSWORD", "PG_DATABASE"
    ])

def get_ai_service_config() -> Dict[str, str]:
    """Get AI service configuration secrets"""
    return secret_manager.get_multiple_secrets([
        "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "OPENAI_API_KEY"
    ])

def validate_production_secrets() -> bool:
    """Validate all required production secrets are available"""
    required_secrets = [
        "PG_HOST", "PG_USERNAME", "PG_PASSWORD", "PG_DATABASE",
        "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION",
        "OPENAI_API_KEY", "JWT_SECRET_KEY", "PHI_ENCRYPTION_KEY"
    ]
    return secret_manager.validate_required_secrets(required_secrets)

if __name__ == "__main__":
    # Test the secret manager
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Simple Secret Manager...")
    
    try:
        # Test all secrets
        print("\n📋 Available Secrets:")
        for key, value in secret_manager.secrets.items():
            masked_value = value[:8] + "..." if len(value) > 8 else value
            print(f"  {key}: {masked_value}")
        
        print("\n🧪 Testing individual secret retrieval:")
        
        # Test database config
        db_config = get_database_config()
        print(f"✅ Database Host: {db_config.get('PG_HOST', 'Missing')}")
        
        # Test Azure Speech
        speech_key = get_secret("AZURE_SPEECH_KEY")
        print(f"✅ Azure Speech Key: {speech_key[:10]}...")
        
        # Test OpenAI
        openai_key = get_secret("OPENAI_API_KEY")
        print(f"✅ OpenAI Key: {openai_key[:15]}...")
        
        # Validate all required secrets
        if validate_production_secrets():
            print("\n🎉 ALL SECRETS VALIDATED - READY FOR PRODUCTION!")
        else:
            print("\n❌ Some secrets are missing")
            
    except Exception as e:
        print(f"❌ Secret manager test failed: {e}")