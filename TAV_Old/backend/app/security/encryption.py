"""
Security encryption utilities.

Provides encryption/decryption for sensitive data stored in the database.
Uses Fernet (symmetric encryption) from cryptography library.
"""

from cryptography.fernet import Fernet
from typing import Optional
import base64
import hashlib


def _get_fernet_key() -> bytes:
    """
    Get Fernet-compatible key from ENCRYPTION_KEY.
    
    Fernet requires a 32-byte base64-encoded key.
    We hash the ENCRYPTION_KEY to ensure it's the right format.
    """
    from app.config import settings
    
    # Hash the encryption key to get consistent 32 bytes
    key_bytes = settings.ENCRYPTION_KEY.encode('utf-8')
    hashed = hashlib.sha256(key_bytes).digest()
    
    # Fernet needs base64-encoded 32 bytes
    return base64.urlsafe_b64encode(hashed)


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value.
    
    Args:
        value: The plaintext string to encrypt
        
    Returns:
        Base64-encoded encrypted string
        
    Example:
        >>> encrypted = encrypt_value("my-secret-api-key")
        >>> print(encrypted)
        'gAAAAABh...'  # Fernet encrypted format
    """
    if not value:
        return value
    
    try:
        fernet = Fernet(_get_fernet_key())
        encrypted_bytes = fernet.encrypt(value.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    except Exception as e:
        # Log error but don't expose details
        raise ValueError(f"Encryption failed: {str(e)}")


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted string value.
    
    Args:
        encrypted_value: The encrypted string (from encrypt_value)
        
    Returns:
        Decrypted plaintext string
        
    Example:
        >>> decrypted = decrypt_value("gAAAAABh...")
        >>> print(decrypted)
        'my-secret-api-key'
    """
    if not encrypted_value:
        return encrypted_value
    
    try:
        fernet = Fernet(_get_fernet_key())
        decrypted_bytes = fernet.decrypt(encrypted_value.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        # Log error but don't expose details
        raise ValueError(f"Decryption failed: {str(e)}")


def is_encrypted(value: str) -> bool:
    """
    Check if a string looks like it's encrypted with Fernet.
    
    Args:
        value: String to check
        
    Returns:
        True if it looks encrypted, False otherwise
        
    Note:
        This is a heuristic check. Fernet encrypted strings start with 'gAAAAA'.
    """
    if not value:
        return False
    
    # Fernet tokens always start with version byte (0x80) encoded in base64
    # which results in 'gAAAAA' at the start
    return value.startswith('gAAAAA')


# Optional: Helper for encrypting multiple values
def encrypt_dict(data: dict, keys_to_encrypt: list[str]) -> dict:
    """
    Encrypt specific keys in a dictionary.
    
    Args:
        data: Dictionary with data
        keys_to_encrypt: List of keys whose values should be encrypted
        
    Returns:
        New dictionary with specified values encrypted
        
    Example:
        >>> data = {"api_key": "secret", "name": "OpenAI"}
        >>> encrypted = encrypt_dict(data, ["api_key"])
        >>> print(encrypted)
        {"api_key": "gAAAAA...", "name": "OpenAI"}
    """
    result = data.copy()
    for key in keys_to_encrypt:
        if key in result and result[key]:
            result[key] = encrypt_value(str(result[key]))
    return result


def decrypt_dict(data: dict, keys_to_decrypt: list[str]) -> dict:
    """
    Decrypt specific keys in a dictionary.
    
    Args:
        data: Dictionary with encrypted data
        keys_to_decrypt: List of keys whose values should be decrypted
        
    Returns:
        New dictionary with specified values decrypted
    """
    result = data.copy()
    for key in keys_to_decrypt:
        if key in result and result[key] and is_encrypted(result[key]):
            result[key] = decrypt_value(result[key])
    return result
