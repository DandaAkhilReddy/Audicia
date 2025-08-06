"""
AUDICIA VOICE-TO-SOAP SYSTEM
Azure Key Vault Secret Management
HIPAA-Compliant Secure Credential Access
"""

import os
import logging
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import AzureError
import structlog

logger = structlog.get_logger()

class AzureSecretManager:
    """
    HIPAA-compliant secret management using Azure Key Vault
    with secure credential caching and error handling
    """
    
    def __init__(self, vault_name: Optional[str] = None):
        # Get vault name from environment or parameter
        self.vault_name = vault_name or os.getenv("AZURE_KEY_VAULT_NAME", "hha-vault-prod")
        self.vault_url = f"https://{self.vault_name}.vault.azure.net"
        
        # Initialize Azure credential
        try:
            # Try managed identity first (for production Azure environments)
            self.credential = ManagedIdentityCredential()
            logger.info("Using Managed Identity for Key Vault access")
        except Exception:
            # Fallback to default credential (for local development)
            self.credential = DefaultAzureCredential()
            logger.info("Using Default Azure Credential for Key Vault access")
        
        # Initialize Key Vault client
        self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)
        
        # Cache for secrets (in-memory only, secure)
        self._secret_cache: Dict[str, str] = {}
        
        logger.info("Azure Key Vault client initialized", vault_url=self.vault_url)
    
    def get_secret(self, secret_name: str, use_cache: bool = True) -> str:
        """
        Retrieve secret from Azure Key Vault with caching and error handling
        
        Args:
            secret_name: Name of the secret in Key Vault
            use_cache: Whether to use cached values (default: True)
            
        Returns:
            Secret value as string
            
        Raises:
            RuntimeError: If secret cannot be retrieved
        """
        # Check cache first
        if use_cache and secret_name in self._secret_cache:
            logger.debug("Retrieved secret from cache", secret_name=secret_name)
            return self._secret_cache[secret_name]
        
        try:
            # Retrieve secret from Key Vault
            retrieved_secret = self.client.get_secret(secret_name)
            secret_value = retrieved_secret.value
            
            # Cache the secret
            if use_cache:
                self._secret_cache[secret_name] = secret_value
            
            logger.info("Successfully retrieved secret from Key Vault", 
                       secret_name=secret_name,
                       secret_version=retrieved_secret.properties.version)
            
            return secret_value
            
        except AzureError as e:
            error_msg = f"Failed to retrieve secret '{secret_name}' from Key Vault: {str(e)}"
            logger.error("Key Vault secret retrieval failed", 
                        secret_name=secret_name, 
                        error=str(e))
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error retrieving secret '{secret_name}': {str(e)}"
            logger.error("Unexpected error in secret retrieval", 
                        secret_name=secret_name, 
                        error=str(e))
            raise RuntimeError(error_msg)
    
    def get_multiple_secrets(self, secret_names: list) -> Dict[str, str]:
        """
        Retrieve multiple secrets efficiently
        
        Args:
            secret_names: List of secret names to retrieve
            
        Returns:
            Dictionary mapping secret names to values
        """
        secrets = {}
        for secret_name in secret_names:
            try:
                secrets[secret_name] = self.get_secret(secret_name)
            except RuntimeError as e:
                logger.warning("Failed to retrieve secret", 
                              secret_name=secret_name, 
                              error=str(e))
                # Continue with other secrets
                continue
        
        logger.info("Retrieved multiple secrets", 
                   requested_count=len(secret_names),
                   retrieved_count=len(secrets))
        return secrets
    
    def validate_required_secrets(self, required_secrets: list) -> bool:
        """
        Validate that all required secrets are available
        
        Args:
            required_secrets: List of secret names that must be present
            
        Returns:
            True if all secrets are available, False otherwise
        """
        missing_secrets = []
        
        for secret_name in required_secrets:
            try:
                self.get_secret(secret_name)
            except RuntimeError:
                missing_secrets.append(secret_name)
        
        if missing_secrets:
            logger.error("Missing required secrets", missing_secrets=missing_secrets)
            return False
        
        logger.info("All required secrets validated successfully")
        return True
    
    def clear_cache(self):
        """Clear the secret cache (for security)"""
        self._secret_cache.clear()
        logger.info("Secret cache cleared")

# Global instance for the application
secret_manager = AzureSecretManager()

# Convenience functions
def get_secret(secret_name: str) -> str:
    """Get a single secret value"""
    return secret_manager.get_secret(secret_name)

def get_database_config() -> Dict[str, str]:
    """Get all database configuration secrets"""
    return secret_manager.get_multiple_secrets([
        "PG_HOST",
        "PG_PORT", 
        "PG_USERNAME",
        "PG_PASSWORD",
        "PG_DATABASE"
    ])

def get_ai_service_config() -> Dict[str, str]:
    """Get AI service configuration secrets"""
    return secret_manager.get_multiple_secrets([
        "AZURE_SPEECH_KEY",
        "AZURE_SPEECH_REGION",
        "OPENAI_API_KEY"
    ])

def validate_production_secrets() -> bool:
    """Validate all required production secrets are available"""
    required_secrets = [
        # Database
        "PG_HOST", "PG_USERNAME", "PG_PASSWORD", "PG_DATABASE",
        # Azure Services
        "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION",
        # AI Services  
        "OPENAI_API_KEY",
        # Security
        "JWT_SECRET_KEY", "PHI_ENCRYPTION_KEY"
    ]
    
    return secret_manager.validate_required_secrets(required_secrets)

if __name__ == "__main__":
    # Test the secret manager
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Test basic functionality
        print("Testing Azure Key Vault connection...")
        
        # Validate required secrets
        if validate_production_secrets():
            print("✅ All production secrets validated successfully!")
        else:
            print("❌ Some production secrets are missing")
        
        # Test individual secret retrieval
        try:
            speech_key = get_secret("AZURE_SPEECH_KEY")
            print(f"✅ Azure Speech Key retrieved: {speech_key[:10]}...")
        except RuntimeError as e:
            print(f"❌ Failed to retrieve Azure Speech Key: {e}")
            
    except Exception as e:
        print(f"❌ Secret manager test failed: {e}")