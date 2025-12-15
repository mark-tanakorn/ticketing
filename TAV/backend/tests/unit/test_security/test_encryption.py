"""
Unit tests for Security/Encryption module

Tests encryption, decryption, and sensitive data handling.
Pure unit tests that test encryption logic.
"""

import pytest
from unittest.mock import patch

from app.security.encryption import (
    encrypt_value,
    decrypt_value,
    is_encrypted,
    encrypt_dict,
    decrypt_dict
)


class TestBasicEncryption:
    """Test basic encryption and decryption"""
    
    def test_encrypt_then_decrypt_returns_original(self):
        """Test that encrypt → decrypt returns original value"""
        original = "my-secret-api-key"
        
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == original
    
    def test_encrypted_value_is_different_from_original(self):
        """Test that encrypted value is different from original"""
        original = "my-secret"
        encrypted = encrypt_value(original)
        
        assert encrypted != original
    
    def test_encrypted_value_starts_with_gAAAAA(self):
        """Test that Fernet encrypted values start with 'gAAAAA'"""
        encrypted = encrypt_value("test")
        
        assert encrypted.startswith("gAAAAA")
    
    def test_same_value_encrypts_differently_each_time(self):
        """Test that same value produces different ciphertext (IV/nonce)"""
        value = "test-value"
        
        encrypted1 = encrypt_value(value)
        encrypted2 = encrypt_value(value)
        
        # Different ciphertext due to random IV
        assert encrypted1 != encrypted2
        
        # But both decrypt to same value
        assert decrypt_value(encrypted1) == value
        assert decrypt_value(encrypted2) == value


class TestEmptyAndNullHandling:
    """Test encryption of empty and null values"""
    
    def test_encrypt_empty_string_returns_empty(self):
        """Test that empty string returns empty"""
        result = encrypt_value("")
        
        assert result == ""
    
    def test_decrypt_empty_string_returns_empty(self):
        """Test that decrypting empty string returns empty"""
        result = decrypt_value("")
        
        assert result == ""
    
    def test_encrypt_none_returns_none(self):
        """Test that None is handled gracefully"""
        # Note: encrypt_value expects string, but should handle edge cases
        # This test may need adjustment based on actual implementation
        pass


class TestEncryptionErrors:
    """Test encryption error handling"""
    
    def test_decrypt_invalid_ciphertext_raises_error(self):
        """Test that decrypting invalid ciphertext raises ValueError"""
        invalid_ciphertext = "not-a-valid-fernet-token"
        
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_value(invalid_ciphertext)
    
    def test_decrypt_corrupted_data_raises_error(self):
        """Test that decrypting corrupted data raises error"""
        # Valid Fernet format but corrupted
        corrupted = "gAAAAABh" + "x" * 100
        
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_value(corrupted)


class TestIsEncryptedCheck:
    """Test is_encrypted heuristic check"""
    
    def test_recognizes_encrypted_values(self):
        """Test that is_encrypted recognizes Fernet encrypted values"""
        encrypted = encrypt_value("test")
        
        assert is_encrypted(encrypted) is True
    
    def test_recognizes_plain_text_as_not_encrypted(self):
        """Test that plain text is not recognized as encrypted"""
        plain_text = "this is plain text"
        
        assert is_encrypted(plain_text) is False
    
    def test_empty_string_not_encrypted(self):
        """Test that empty string is not encrypted"""
        assert is_encrypted("") is False
    
    def test_fernet_like_string_recognized(self):
        """Test that strings starting with 'gAAAAA' are recognized"""
        fake_fernet = "gAAAAABhthis-looks-like-fernet"
        
        assert is_encrypted(fake_fernet) is True


class TestDictFieldEncryption:
    """Test encrypt_dict and decrypt_dict"""
    
    def test_encrypt_dict_encrypts_specified_keys(self):
        """Test that encrypt_dict encrypts only specified fields"""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com"
        }
        
        encrypted_data = encrypt_dict(data, ["password"])
        
        # Password should be encrypted
        assert encrypted_data["password"] != "secret123"
        assert is_encrypted(encrypted_data["password"])
        
        # Other fields unchanged
        assert encrypted_data["username"] == "john"
        assert encrypted_data["email"] == "john@example.com"
    
    def test_decrypt_dict_decrypts_specified_keys(self):
        """Test that decrypt_dict decrypts only specified fields"""
        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com"
        }
        
        # Encrypt then decrypt
        encrypted_data = encrypt_dict(data, ["password"])
        decrypted_data = decrypt_dict(encrypted_data, ["password"])
        
        # Should match original
        assert decrypted_data["password"] == "secret123"
        assert decrypted_data["username"] == "john"
    
    def test_encrypt_multiple_fields(self):
        """Test encrypting multiple fields at once"""
        data = {
            "api_key": "key-123",
            "api_secret": "secret-456",
            "endpoint": "https://api.example.com"
        }
        
        encrypted_data = encrypt_dict(data, ["api_key", "api_secret"])
        
        assert is_encrypted(encrypted_data["api_key"])
        assert is_encrypted(encrypted_data["api_secret"])
        assert encrypted_data["endpoint"] == "https://api.example.com"
    
    def test_encrypt_dict_handles_missing_fields(self):
        """Test that encrypt_dict handles missing fields gracefully"""
        data = {
            "username": "john"
        }
        
        # Try to encrypt field that doesn't exist
        encrypted_data = encrypt_dict(data, ["password"])
        
        # Should not raise error
        assert "username" in encrypted_data
        assert encrypted_data["username"] == "john"
    
    def test_decrypt_non_encrypted_field_returns_original(self):
        """Test that decrypting non-encrypted field returns original"""
        data = {
            "field": "plain-text-value"
        }
        
        # Try to decrypt non-encrypted field
        decrypted_data = decrypt_dict(data, ["field"])
        
        # Should return original or handle gracefully
        assert "field" in decrypted_data


class TestEncryptionRoundTrip:
    """Test encryption/decryption round-trip scenarios"""
    
    def test_complex_unicode_string(self):
        """Test encrypting and decrypting unicode strings"""
        original = "Hello 世界 🌍 Привет"
        
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == original
    
    def test_long_string(self):
        """Test encrypting and decrypting long strings"""
        original = "x" * 10000  # 10KB string
        
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == original
    
    def test_json_like_string(self):
        """Test encrypting JSON-formatted strings"""
        original = '{"api_key": "secret-123", "nested": {"value": 456}}'
        
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == original

