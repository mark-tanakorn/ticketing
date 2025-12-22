# Credentials & Encryption Reference

The TAV Engine provides secure credential storage with encryption at rest. This document covers the credential management system and encryption utilities.

---

## Overview

Credentials are stored encrypted in the database using **Fernet symmetric encryption** (AES-128-CBC with HMAC). The system:

- Encrypts sensitive fields before storing
- Decrypts on-demand when needed by nodes
- Supports multiple credential types (API keys, OAuth, SMTP, etc.)
- Tracks usage with `last_used_at` timestamps

---

## Encryption System

Located at `backend/app/security/encryption.py`.

### How It Works

```
ENCRYPTION_KEY (from config)
    ↓ SHA-256 hash
32-byte key
    ↓ base64 encode
Fernet key
    ↓
Encrypt/Decrypt values
```

### Functions

#### `encrypt_value(value: str) -> str`

Encrypt a single string value.

```python
from app.security.encryption import encrypt_value

encrypted = encrypt_value("my-secret-api-key")
# Returns: "gAAAAABh..." (Fernet token)
```

#### `decrypt_value(encrypted_value: str) -> str`

Decrypt an encrypted string.

```python
from app.security.encryption import decrypt_value

plaintext = decrypt_value("gAAAAABh...")
# Returns: "my-secret-api-key"
```

#### `encrypt_dict(data: dict, keys_to_encrypt: list) -> dict`

Encrypt specific keys in a dictionary.

```python
from app.security.encryption import encrypt_dict

data = {"api_key": "secret", "name": "OpenAI"}
encrypted = encrypt_dict(data, ["api_key"])
# Returns: {"api_key": "gAAAAABh...", "name": "OpenAI"}
```

#### `decrypt_dict(data: dict, keys_to_decrypt: list) -> dict`

Decrypt specific keys in a dictionary.

```python
from app.security.encryption import decrypt_dict

data = {"api_key": "gAAAAABh...", "name": "OpenAI"}
decrypted = decrypt_dict(data, ["api_key"])
# Returns: {"api_key": "secret", "name": "OpenAI"}
```

#### `is_encrypted(value: str) -> bool`

Check if a string is Fernet-encrypted.

```python
from app.security.encryption import is_encrypted

is_encrypted("gAAAAABh...")  # True
is_encrypted("plain-text")   # False
```

### Configuration

The encryption key is set via environment variable:

```bash
# .env file
ENCRYPTION_KEY=your-secret-key-here
```

> **Important**: Use a strong, unique key. If lost, all encrypted data becomes unrecoverable.

---

## Credential Manager

Located at `backend/app/services/credential_manager.py`.

High-level service for credential CRUD operations with automatic encryption.

### Usage

```python
from app.services.credential_manager import CredentialManager
from app.schemas.credential import CredentialCreate, AuthType

manager = CredentialManager(db)

# Create credential (automatically encrypted)
credential = manager.create_credential(
    user_id=1,
    credential_data=CredentialCreate(
        name="OpenAI API",
        service_type="openai",
        auth_type=AuthType.API_KEY,
        credential_data={"api_key": "sk-..."},
        description="Production API key"
    )
)

# Get credential (without sensitive data)
cred = manager.get_credential(credential.id, user_id=1)

# Get credential with decrypted data
cred_with_data = manager.get_credential(credential.id, user_id=1, include_data=True)

# Get raw data for injection into nodes
data = manager.get_credential_data(credential.id)
# Returns: {"api_key": "sk-..."} (decrypted)
```

### Methods

| Method | Description |
|--------|-------------|
| `create_credential()` | Create new credential (auto-encrypts) |
| `get_credential()` | Get credential (optionally with decrypted data) |
| `list_credentials()` | List user's credentials (no sensitive data) |
| `update_credential()` | Update credential (auto-re-encrypts) |
| `delete_credential()` | Delete credential |
| `get_credential_data()` | Get decrypted data for node injection |
| `get_credential_types()` | Get available credential type definitions |

---

## Credential Types

The system supports predefined credential types with field definitions.

### Built-in Types

#### API Key (`api_key`)
```json
{
  "api_key": "sk-..."
}
```
Fields: `api_key` (encrypted)

#### Bearer Token (`bearer_token`)
```json
{
  "token": "eyJ..."
}
```
Fields: `token` (encrypted)

#### Basic Auth (`basic_auth`)
```json
{
  "username": "user",
  "password": "secret"
}
```
Fields: `username` (plain), `password` (encrypted)

#### OAuth 2.0 (`oauth2`)
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "client_id": "...",
  "client_secret": "...",
  "token_expiry": "2024-12-01T00:00:00Z"
}
```
Fields: `access_token`, `refresh_token`, `client_secret` (encrypted); others plain

#### SMTP (`smtp`)
```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "user@gmail.com",
  "password": "app-password",
  "use_tls": true
}
```
Fields: `password` (encrypted); others plain

#### Database (`database`)
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "username": "admin",
  "password": "secret"
}
```
Fields: `password` (encrypted); others plain

#### Twilio (`twilio`)
```json
{
  "account_sid": "AC...",
  "auth_token": "...",
  "phone_number": "+14155238886"
}
```
Fields: `auth_token` (encrypted); others plain

#### Custom (`custom`)
Any JSON object. All fields encrypted by default.

---

## Database Schema

### `credentials` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `user_id` | INTEGER | Owner user ID |
| `name` | VARCHAR | Display name |
| `service_type` | VARCHAR | Service identifier (e.g., "openai") |
| `auth_type` | VARCHAR | Authentication type (enum) |
| `encrypted_data` | TEXT | JSON with encrypted fields |
| `config_metadata` | TEXT | Non-sensitive metadata (JSON) |
| `description` | TEXT | User description |
| `is_active` | BOOLEAN | Whether credential is active |
| `created_at` | DATETIME | Creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |
| `last_used_at` | DATETIME | Last access timestamp |

---

## Using Credentials in Nodes

Nodes can access credentials via the execution context:

```python
class MyNode(BaseNode):
    CONFIG_SCHEMA = [
        {
            "name": "credential_id",
            "type": "credential",
            "label": "API Credential",
            "service_type": "openai"  # Filter by service type
        }
    ]
    
    async def process(self, inputs, config, context):
        credential_id = config.get("credential_id")
        
        if credential_id:
            # Get decrypted credential data
            from app.services.credential_manager import CredentialManager
            manager = CredentialManager(context.db)
            cred_data = manager.get_credential_data(credential_id)
            
            api_key = cred_data.get("api_key")
            # Use api_key...
```

---

## Security Best Practices

### Encryption Key Management

1. **Use a strong key**: At least 32 characters, random
2. **Don't commit to git**: Use environment variables or secrets manager
3. **Rotate periodically**: (requires re-encrypting all credentials)
4. **Backup securely**: If lost, data is unrecoverable

### Access Control

1. **User isolation**: Credentials are filtered by `user_id`
2. **Minimize exposure**: `get_credential()` doesn't return data by default
3. **Audit trail**: `last_used_at` tracks access
4. **Soft delete**: Consider using `is_active=False` instead of hard delete

### In Transit

1. **HTTPS only**: Never transmit credentials over plain HTTP
2. **Don't log secrets**: Ensure logging doesn't capture decrypted values
3. **Mask in UI**: Show `api_key: "sk-...abc"` not full value

---

## API Endpoints

Credentials are managed via REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/credentials` | GET | List user's credentials |
| `/api/v1/credentials` | POST | Create credential |
| `/api/v1/credentials/{id}` | GET | Get credential |
| `/api/v1/credentials/{id}` | PATCH | Update credential |
| `/api/v1/credentials/{id}` | DELETE | Delete credential |
| `/api/v1/credentials/types` | GET | Get credential type definitions |

---

## Troubleshooting

### "Decryption failed"

- **Cause**: Wrong encryption key or corrupted data
- **Solution**: Verify `ENCRYPTION_KEY` matches what was used to encrypt

### "Required field missing"

- **Cause**: Missing required field for credential type
- **Solution**: Check credential type definition for required fields

### "Credential not found"

- **Cause**: Invalid ID or wrong user
- **Solution**: Credentials are user-scoped; verify ownership

---

## Related Documentation

- [Database Architecture](../architecture/database.md) - Credentials table schema
- [Node System](../architecture/nodes.md) - Using credentials in nodes
- [Settings API](../api/settings.md) - System-wide encryption settings

