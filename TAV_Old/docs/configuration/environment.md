# 🔧 Environment Configuration Guide

## Overview

TAV Engine uses a **2-tier configuration system**:

1. **Environment Variables** (`.env` file) → Infrastructure & Secrets
2. **Database Settings** → Application behavior & user preferences

---

## 📁 Configuration Files Map

```
tav_opensource/
│
├── .env (YOU CREATE THIS - Git ignored)
│   └── Your actual secrets and configuration
│
├── deployment/configs/
│   ├── env.unified.example   ← Main template (copy to .env)
│   ├── env.local.example     ← For LAN access
│   └── env.production.example ← For production
│
└── backend/
    ├── app/
    │   ├── config.py ⭐ MAIN CONFIG FILE
    │   │   └── Loads .env variables using Pydantic
    │   │
    │   ├── database/
    │   │   └── models/
    │   │       └── setting.py
    │   │           └── Database model for app settings
    │   │
    │   └── core/
    │       └── config/
    │           └── manager.py
    │               └── Manages database-stored settings
    │
    └── tests/
        └── conftest.py
            └── Sets test environment variables
```

---

## 🎯 The 2-Tier System Explained

### Tier 1: Environment Variables (`.env` file)
**Purpose**: Infrastructure, secrets, deployment-specific settings

**File**: `backend/app/config.py`
**Loads from**: `.env` file in root directory
**Used for**:
- ✅ SECRET_KEY (JWT signing)
- ✅ ENCRYPTION_KEY (encrypting sensitive DB data)
- ✅ DATABASE_URL (where your DB is)
- ✅ API keys (OpenAI, Anthropic, etc.)
- ✅ OAuth credentials
- ✅ CORS origins
- ✅ Environment (dev/staging/prod)

**Why separate?**:
- Never committed to Git (security)
- Different per environment (dev vs prod)
- Infrastructure-level concerns

### Tier 2: Database Settings
**Purpose**: Application behavior, user preferences, feature flags

**File**: `backend/app/database/models/setting.py`
**Managed by**: `backend/app/core/config/manager.py`
**Used for**:
- ✅ AI model preferences (temperature, max_tokens)
- ✅ UI settings (theme, language)
- ✅ Workflow timeouts
- ✅ Execution settings
- ✅ Feature flags
- ✅ User-configurable settings

**Why in database?**:
- Can be changed without redeploying
- Can be modified via UI/API
- User-specific settings
- Audit trail of changes

---

## 📋 What Goes Where?

### ❓ Should it be in `.env`?

**YES** → If it's:
- A secret/credential
- Infrastructure-related
- Different per environment
- Never shown to users
- Required to START the app

**NO** → If it's:
- User-configurable
- Application logic
- Can change at runtime
- Needs audit trail
- Shown in UI

---

## 🔑 Critical Environment Variables

### REQUIRED (App won't start without these):

```bash
# backend/app/config.py lines 36 & 75
SECRET_KEY=...      # JWT signing (32+ chars)
ENCRYPTION_KEY=...  # DB encryption (32 bytes)
```

### OPTIONAL (Have defaults):

```bash
DATABASE_URL=sqlite:///./data/tav_engine.db  # Default: SQLite
ENVIRONMENT=development                      # Default: development
LOG_LEVEL=INFO                               # Default: INFO
```

---

## 🚀 Quick Setup

### Step 1: Create Your `.env` File

```bash
# From project root
cp deployment/configs/env.unified.example .env
```

### Step 2: Edit Required Values

```bash
# Open .env and change these:
SECRET_KEY=change-this-to-random-string-min-32-chars
ENCRYPTION_KEY=change-this-32-byte-encryption-key!
```

### Step 3: (Optional) Add API Keys

```bash
# Add to .env if you want to use AI features:
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## 🧪 Testing Environment

**File**: `backend/tests/conftest.py`

Sets test-specific environment variables:

```python
os.environ["SECRET_KEY"] = "test-secret-key..."
os.environ["ENCRYPTION_KEY"] = "test-encryption-key..."
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "testing"
```

**Why?**: Tests need valid config but shouldn't use production values.

---

## 📖 How It Works (Flow)

```
1. App Starts
   ↓
2. backend/app/config.py loads
   ↓
3. Pydantic reads .env file
   ↓
4. Validates required variables
   ↓
5. Creates Settings object
   ↓
6. App uses settings.SECRET_KEY, etc.
```

For database settings:
```
1. User requests setting
   ↓
2. API calls SettingsManager
   ↓
3. Reads from database
   ↓
4. Returns value (uses cache)
```

---

## 🎨 Example: Where Each Setting Lives

| Setting | Location | Why |
|---------|----------|-----|
| `SECRET_KEY` | `.env` | Secret, never changes at runtime |
| `DATABASE_URL` | `.env` | Infrastructure, different per environment |
| `OPENAI_API_KEY` | `.env` OR DB | Can be in either (DB is more flexible) |
| `AI_MODEL_TEMPERATURE` | Database | Users can change via UI |
| `WORKFLOW_TIMEOUT` | Database | Business logic, not infrastructure |
| `ENABLE_METRICS` | `.env` | Infrastructure decision |
| `THEME_COLOR` | Database | User preference |

---

## 🔍 Key Files Reference

### 1. `deployment/configs/env.unified.example`
Main template for `.env` file. Shows all available variables.

### 2. `backend/app/config.py` (Line 1-113)
**THE MAIN CONFIG FILE** - Loads environment variables.

**Key sections**:
- Lines 43-49: Settings class definition
- Line 97-100: SECRET_KEY
- Line 172-175: ENCRYPTION_KEY
- Line 137-158: Database config
- Line 180-192: AI provider keys (optional)
- Line 209-212: Tells Pydantic to read `.env`
- Line 218: Creates global `settings` object

### 3. `backend/app/database/models/setting.py`
Database model for application settings (Tier 2).

### 4. `backend/app/core/config/manager.py`
Manages database-stored settings with caching.

### 5. `backend/tests/conftest.py`
Sets test environment variables before tests run.

---

## ⚠️ Common Issues

### Issue 1: "SECRET_KEY Field required"
**Cause**: No `.env` file or missing SECRET_KEY
**Fix**: Create `.env` from `env.example` and set SECRET_KEY

### Issue 2: "ENCRYPTION_KEY Field required"
**Cause**: Missing ENCRYPTION_KEY in `.env`
**Fix**: Add ENCRYPTION_KEY=your-32-char-key-here to `.env`

### Issue 3: Tests fail with validation errors
**Cause**: Test environment not set up
**Fix**: Already fixed in `tests/conftest.py` - sets test env vars

---

## 🎯 To Get Started RIGHT NOW

1. **Create `.env` file**:
```bash
# From project root
cp deployment/configs/env.unified.example .env
```

2. **Edit `.env`** - Change these two lines:
```bash
SECRET_KEY=my-super-secret-key-at-least-32-characters-long-please
ENCRYPTION_KEY=my-encryption-key-exactly-32b!
```

3. **That's it!** Your app can now start.

---

## 📝 Summary

**Environment Variables** (`.env` → `config.py`):
- Infrastructure settings
- Secrets and keys
- Connection strings
- Never committed to Git

**Database Settings** (`setting.py` → `manager.py`):
- Application behavior
- User preferences  
- Runtime-changeable
- UI-configurable

**For your tests**: `tests/conftest.py` sets test env vars automatically.

