"""
Encryption utilities for secure credential storage.

This module provides Fernet symmetric encryption for storing sensitive
credentials like Vultr API keys. It supports key rotation by storing
a key identifier with each encrypted value.
"""

import os
from typing import Tuple
from cryptography.fernet import Fernet, InvalidToken
import structlog

logger = structlog.get_logger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption operations."""
    pass


class EncryptionKeyError(EncryptionError):
    """Raised when encryption key is missing or invalid."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    pass


def get_encryption_key(key_id: str = "default") -> bytes:
    """
    Get encryption key by ID from environment variables.

    Args:
        key_id: Identifier for the encryption key (default: "default")

    Returns:
        Fernet encryption key as bytes

    Raises:
        EncryptionKeyError: If key is not found or invalid

    Environment Variables:
        FERNET_KEY: Primary encryption key (base64-encoded 32-byte key)
        FERNET_KEY_{KEY_ID}: Additional keys for rotation (e.g., FERNET_KEY_OLD)
    """
    # Normalize key_id to uppercase for environment variable lookup
    env_var = f"FERNET_KEY_{key_id.upper()}" if key_id != "default" else "FERNET_KEY"

    key = os.getenv(env_var)
    if not key:
        logger.error(f"Encryption key not found", key_id=key_id, env_var=env_var)
        raise EncryptionKeyError(
            f"Encryption key '{env_var}' not found in environment. "
            f"Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    # Validate key format
    try:
        # Fernet.generate_key() produces base64-encoded 32-byte keys
        key_bytes = key.encode('utf-8')
        # Test that it's a valid Fernet key by creating a Fernet instance
        Fernet(key_bytes)
        return key_bytes
    except Exception as e:
        logger.error(f"Invalid encryption key format", key_id=key_id, error=str(e))
        raise EncryptionKeyError(
            f"Encryption key '{env_var}' is not a valid Fernet key: {str(e)}"
        )


def encrypt_value(plaintext: str, key_id: str = "default") -> Tuple[str, str]:
    """
    Encrypt a plaintext value using Fernet symmetric encryption.

    Args:
        plaintext: The value to encrypt (e.g., Vultr API key)
        key_id: Identifier for the encryption key to use

    Returns:
        Tuple of (encrypted_value, key_id) where encrypted_value is base64-encoded

    Raises:
        EncryptionError: If encryption fails

    Example:
        >>> encrypted, key_id = encrypt_value("my-vultr-api-key-here")
        >>> # Store both encrypted and key_id in database
    """
    try:
        key = get_encryption_key(key_id)
        fernet = Fernet(key)

        # Encrypt the plaintext
        encrypted_bytes = fernet.encrypt(plaintext.encode('utf-8'))
        encrypted_str = encrypted_bytes.decode('utf-8')

        logger.debug("Value encrypted successfully", key_id=key_id)
        return encrypted_str, key_id

    except EncryptionKeyError:
        raise  # Re-raise key errors
    except Exception as e:
        logger.error("Encryption failed", key_id=key_id, error=str(e), exc_info=True)
        raise EncryptionError(f"Failed to encrypt value: {str(e)}")


def decrypt_value(encrypted_value: str, key_id: str = "default") -> str:
    """
    Decrypt an encrypted value using Fernet symmetric encryption.

    Args:
        encrypted_value: Base64-encoded encrypted value
        key_id: Identifier for the encryption key used

    Returns:
        Decrypted plaintext value

    Raises:
        DecryptionError: If decryption fails
        EncryptionKeyError: If encryption key is not found

    Example:
        >>> api_key = decrypt_value(encrypted_value, key_id)
        >>> # Use api_key for Vultr API calls
    """
    try:
        key = get_encryption_key(key_id)
        fernet = Fernet(key)

        # Decrypt the value
        encrypted_bytes = encrypted_value.encode('utf-8')
        decrypted_bytes = fernet.decrypt(encrypted_bytes)
        plaintext = decrypted_bytes.decode('utf-8')

        logger.debug("Value decrypted successfully", key_id=key_id)
        return plaintext

    except EncryptionKeyError:
        raise  # Re-raise key errors
    except InvalidToken as e:
        logger.error("Decryption failed - invalid token or wrong key",
                    key_id=key_id, error=str(e))
        raise DecryptionError(
            f"Failed to decrypt value with key '{key_id}'. "
            "This may indicate data corruption or wrong encryption key."
        )
    except Exception as e:
        logger.error("Decryption failed", key_id=key_id, error=str(e), exc_info=True)
        raise DecryptionError(f"Failed to decrypt value: {str(e)}")


def rotate_encryption(encrypted_value: str, old_key_id: str, new_key_id: str = "default") -> Tuple[str, str]:
    """
    Rotate encryption from one key to another.

    This is useful for key rotation scenarios where you need to re-encrypt
    data with a new encryption key.

    Args:
        encrypted_value: Currently encrypted value
        old_key_id: Key ID used for current encryption
        new_key_id: Key ID to use for new encryption

    Returns:
        Tuple of (new_encrypted_value, new_key_id)

    Raises:
        DecryptionError: If decryption with old key fails
        EncryptionError: If encryption with new key fails

    Example:
        >>> # Rotate from old key to new key
        >>> new_encrypted, new_key_id = rotate_encryption(
        ...     encrypted_value, old_key_id="old", new_key_id="default"
        ... )
    """
    # Decrypt with old key
    plaintext = decrypt_value(encrypted_value, old_key_id)

    # Re-encrypt with new key
    new_encrypted, key_id = encrypt_value(plaintext, new_key_id)

    logger.info("Encryption rotated successfully",
                old_key_id=old_key_id, new_key_id=key_id)

    return new_encrypted, key_id


# Convenience function for generating new Fernet keys
def generate_fernet_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        Base64-encoded Fernet key as string

    Example:
        >>> key = generate_fernet_key()
        >>> print(f"Add to .env: FERNET_KEY={key}")
    """
    return Fernet.generate_key().decode('utf-8')


if __name__ == "__main__":
    # Helper script for generating encryption keys
    print("=" * 60)
    print("Fernet Encryption Key Generator")
    print("=" * 60)
    print()
    print("Generated encryption key (add to .env):")
    print()
    print(f"FERNET_KEY={generate_fernet_key()}")
    print()
    print("For key rotation, you can generate additional keys:")
    print(f"FERNET_KEY_OLD={generate_fernet_key()}")
    print()
    print("=" * 60)
