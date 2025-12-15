# Database Architecture

Complete reference for TAV Engine's database structure.

---

## Overview

TAV Engine uses **SQLite** for data storage - a lightweight, file-based database that requires no separate server or configuration.

**Database File:** `backend/data/tav_engine.db`

**Why SQLite?**
- ✅ Zero configuration required
- ✅ Single file (easy to backup)
- ✅ Built into Python
- ✅ Perfect for self-hosted, single-instance deployments
- ✅ Handles thousands of workflows easily

---

## Table of Contents

- [Database Tables](#database-tables)
- [Table Relationships](#table-relationships)
- [Key Tables Details](#key-tables-details)
- [Migrations](#migrations)
- [Backup & Recovery](#backup--recovery)
- [Performance](#performance)

---

## Database Tables

TAV Engine has **14 core tables:**

### Core Workflow Tables
1. **`workflows`** - Workflow definitions (nodes, connections, config)
2. **`executions`** - Workflow execution runs
3. **`execution_results`** - Execution output data
4. **`execution_logs`** - Detailed execution logs
5. **`execution_iterations`** - Loop iteration tracking
6. **`workflow_state`** - Persistent state storage for workflows

### User & Security
7. **`users`** - User accounts (system and admin users)
8. **`api_keys`** - API authentication tokens
9. **`credentials`** - Encrypted credentials (API keys, passwords)

### System
10. **`settings`** - Application configuration (key-value store)
11. **`files`** - Uploaded file metadata
12. **`email_interactions`** - Email approval workflows
13. **`event_queue`** - Trigger event queue
14. **`audit_logs`** - System audit trail

---

## Table Relationships

```
users (1) ──────┬────────> workflows (many)
                │
                └────────> api_keys (many)

workflows (1) ──────────> executions (many)
          (1) ──────────> workflow_state (many)

executions (1) ─────────> execution_results (many)
           (1) ─────────> execution_logs (many)
           (1) ─────────> execution_iterations (many)

workflows (1) ──────────> email_interactions (many)
```

---

## Key Tables Details

### workflows

**Purpose:** Store workflow definitions

**Key Columns:**
- `id` (string, PK): Workflow UUID
- `name` (string): Workflow name
- `description` (text): Description
- `version` (string): Version number
- `workflow_data` (JSON): Complete workflow structure (nodes, connections, config)
- `tags` (JSON): Array of tags for categorization
- `author_id` (int, FK): Creator user ID
- `execution_config` (JSON): Execution settings override
- `status` (string): Current status (na, pending, running, completed, failed, stopped, paused)
- `last_execution_id` (string, FK): Most recent execution
- `is_active` (boolean): Whether workflow is active
- `is_template` (boolean): Whether workflow is a template
- `template_category` (string): Category for templates
- `recommended_await_completion` (string): Hint for sync/async execution
- `monitoring_started_at` (datetime): When monitoring started
- `monitoring_stopped_at` (datetime): When monitoring stopped
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp
- `last_run_at` (datetime): Last execution timestamp

**Indexes:**
- `idx_workflows_name`: On name
- `idx_workflows_status`: On status
- `idx_workflows_author_id`: On author_id
- `idx_workflows_created_at`: On created_at
- `idx_workflows_last_run_at`: On last_run_at
- `idx_workflows_template_category`: On template_category

**workflow_data JSON Structure:**
```json
{
  "workflow_id": "uuid",
  "name": "Workflow Name",
  "format_version": "2.0.0",
  "nodes": [
    {
      "node_id": "node_1",
      "node_type": "text_input",
      "name": "Input",
      "category": "input",
      "config": {...},
      "position": {"x": 100, "y": 100}
    }
  ],
  "connections": [
    {
      "source_node_id": "node_1",
      "source_port": "output",
      "target_node_id": "node_2",
      "target_port": "input"
    }
  ],
  "canvas_objects": [],
  "global_config": {},
  "variables": {},
  "metadata": {}
}
```

---

### executions

**Purpose:** Track workflow execution runs

**Key Columns:**
- `id` (string, PK): Execution UUID
- `workflow_id` (string, FK): Parent workflow
- `status` (string): Current status (pending, running, completed, failed, cancelled)
- `started_by` (string): User who started execution
- `execution_source` (string): How started (manual, schedule, webhook, etc.)
- `execution_mode` (string): Mode (parallel, sequential)
- `trigger_data` (JSON): Data from trigger (if applicable)
- `final_outputs` (JSON): Final workflow outputs
- `node_results` (JSON): Results from all nodes
- `execution_log` (JSON): Execution timeline
- `execution_metadata` (JSON): Additional metadata
- `started_at` (datetime): Start timestamp
- `completed_at` (datetime): Completion timestamp
- `cancelled_at` (datetime): Cancellation timestamp

**Indexes:**
- `idx_executions_workflow_id`: On workflow_id
- `idx_executions_status`: On status
- `idx_executions_started_at`: On started_at

**Retention:**
- Configurable in Settings → Storage
- Default: Keep 100 most recent per workflow
- Cleanup interval: Configurable

---

### execution_results

**Purpose:** Store execution output data

**Key Columns:**
- `id` (bigint, PK): Auto-increment ID
- `execution_id` (string, FK): Parent execution
- `node_id` (string): Node that produced result
- `port_name` (string): Output port name
- `data_type` (string): Data type (text, image, file, etc.)
- `content` (text): Actual data content
- `file_path` (string): Path to file (if applicable)
- `content_projection` (text): Truncated preview for large data
- `byte_size` (int): Size in bytes
- `created_at` (datetime): Creation timestamp

**Indexes:**
- `idx_execution_results_execution_id`: On execution_id
- `idx_execution_results_node_id`: On node_id

---

### execution_iterations

**Purpose:** Track loop iterations (for Loop Orchestrator nodes)

**Key Columns:**
- `id` (bigint, PK): Auto-increment ID
- `execution_id` (string, FK): Parent execution
- `loop_node_id` (string): Loop node ID
- `iteration_number` (int): Current iteration (0-based)
- `iteration_value` (JSON): Value for this iteration
- `iteration_index` (int): Index in iteration array
- `status` (string): Status (pending, running, completed, failed)
- `started_at` (datetime): Start timestamp
- `completed_at` (datetime): Completion timestamp
- `outputs` (JSON): Iteration outputs
- `error_message` (text): Error if failed

**Use Case:**
```python
# Loop over [1, 2, 3, 4, 5]
# Creates 5 execution_iteration records tracking each loop
```

---

### workflow_state

**Purpose:** Persistent state storage for business logic

**Key Columns:**
- `id` (bigint, PK): Auto-increment ID
- `workflow_id` (string, FK): Workflow that owns this state
- `state_key` (string): State variable name
- `state_value` (JSON): State value (any JSON type)
- `value_type` (string): Type hint (string, number, object, array)
- `description` (text): Description of state variable
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp
- `accessed_at` (datetime): Last access timestamp
- `access_count` (int): Number of accesses
- `ttl_seconds` (int): Time-to-live (null = permanent)
- `expires_at` (datetime): Expiration timestamp

**Indexes:**
- `idx_workflow_state_workflow_key`: On (workflow_id, state_key) - Unique
- `idx_workflow_state_expires_at`: On expires_at

**Use Case:**
```python
# Business logic nodes (State Get/Set/Update)
# Store: inventory, counters, flags, configuration
# Persists across executions
```

---

### users

**Purpose:** User accounts and authentication

**Key Columns:**
- `id` (int, PK): User ID
- `user_name` (string): Username
- `user_email` (string): Email address
- `user_password` (string): Hashed password
- `user_firstname` (string): First name
- `user_lastname` (string): Last name
- `user_status` (string): Account status (active, inactive, locked)
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp

**Special Users:**
- **System User (ID: 1)**: Used for internal operations and dev mode
- **Admin Users**: Created manually via scripts

**Indexes:**
- `idx_users_username`: On user_name (unique)
- `idx_users_email`: On user_email (unique)

---

### credentials

**Purpose:** Store encrypted credentials (API keys, passwords)

**Key Columns:**
- `id` (int, PK): Credential ID
- `user_id` (int, FK): Owner user ID
- `name` (string): Credential name
- `credential_type` (string): Type (api_key, basic_auth, oauth2, etc.)
- `encrypted_data` (text): Encrypted credential data
- `description` (text): Description
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp
- `last_used_at` (datetime): Last usage timestamp

**Security:**
- All credential data is encrypted using AES-256
- Encryption key from environment variable
- Decrypted only when needed during execution

**Use Case:**
```python
# Store API keys for external services
# Reference in node configs: {"credential_id": 123}
# Executor decrypts at runtime
```

---

### files

**Purpose:** Track uploaded files

**Key Columns:**
- `id` (int, PK): File ID
- `workflow_id` (string, FK): Associated workflow
- `execution_id` (string, FK): Associated execution
- `original_filename` (string): Original name
- `stored_filename` (string): Storage name (UUID-based)
- `file_path` (string): Full path to file
- `file_type` (string): Type (document, image, audio, video, etc.)
- `mime_type` (string): MIME type
- `size_bytes` (bigint): File size
- `file_metadata` (JSON): File metadata (dimensions, duration, etc.)
- `created_at` (datetime): Upload timestamp

**Indexes:**
- `idx_files_workflow_id`: On workflow_id
- `idx_files_execution_id`: On execution_id
- `idx_files_created_at`: On created_at

**Storage:**
- Files stored in `backend/data/uploads/`
- Organized by type (document/, image/, audio/, video/, etc.)
- Cleanup based on storage settings

---

### settings

**Purpose:** Application configuration (key-value store)

**Key Columns:**
- `id` (int, PK): Setting ID
- `category` (string): Category (execution, ai, ui, storage, etc.)
- `key` (string): Setting key
- `value` (JSON): Setting value (any JSON type)
- `updated_at` (datetime): Last update timestamp
- `updated_by` (string): User who updated

**Indexes:**
- `idx_settings_category_key`: On (category, key) - Unique

**Categories:**
- `execution`: Execution behavior settings
- `ai`: AI provider configuration
- `ui`: User interface defaults
- `storage`: Storage and cleanup policies
- `security`: Security settings
- `network`: Network configuration
- `integrations`: Third-party integrations
- `developer`: Development settings

**Example Records:**
```sql
category='execution', key='max_concurrent_nodes', value='5'
category='ai', key='default_provider', value='"openai"'
category='ui', key='default_theme_mode', value='"dark"'
```

---

### email_interactions

**Purpose:** Store email approval workflow data

**Key Columns:**
- `id` (bigint, PK): Interaction ID
- `interaction_id` (string): Public interaction UUID
- `workflow_id` (string, FK): Associated workflow
- `execution_id` (string, FK): Associated execution
- `node_id` (string): Email node ID
- `interaction_type` (string): Type (approval, input, feedback)
- `email_data` (JSON): Email content and metadata
- `status` (string): Status (pending, approved, rejected, expired)
- `response_data` (JSON): User response data
- `created_at` (datetime): Creation timestamp
- `responded_at` (datetime): Response timestamp
- `expires_at` (datetime): Expiration timestamp

**Use Case:**
```python
# Email Approval node sends email with unique link
# User clicks link → opens review page
# User approves/rejects → stored here
# Workflow resumes with response
```

---

### event_queue

**Purpose:** Queue for trigger events

**Key Columns:**
- `id` (bigint, PK): Event ID
- `workflow_id` (string, FK): Workflow to execute
- `event_type` (string): Event type (schedule, file_detected, email_received)
- `event_data` (JSON): Event payload
- `priority` (int): Priority (1=high, 5=low)
- `status` (string): Status (pending, processing, completed, failed)
- `created_at` (datetime): Creation timestamp
- `processed_at` (datetime): Processing timestamp
- `attempts` (int): Processing attempts
- `error_message` (text): Error if failed

**Indexes:**
- `idx_event_queue_workflow_priority`: On (workflow_id, priority, status)
- `idx_event_queue_created_at`: On created_at

**Use Case:**
```python
# Trigger fires → Creates event in queue
# TriggerManager processes queue → Spawns execution
# Respects concurrency limits via queue
```

---

## Table Relationships

### Workflow Hierarchy

```
users (1)
  └─> workflows (many)
        ├─> executions (many)
        │     ├─> execution_results (many)
        │     ├─> execution_logs (many)
        │     └─> execution_iterations (many)
        │
        ├─> workflow_state (many)
        ├─> email_interactions (many)
        ├─> event_queue (many)
        └─> files (many)
```

### Execution Tracking

```
workflow
  └─> execution
        ├─> execution_results (output data from each node)
        ├─> execution_logs (log entries)
        └─> execution_iterations (loop tracking)
```

### Security Relationships

```
users
  ├─> workflows (created workflows)
  ├─> api_keys (authentication)
  └─> credentials (owned credentials)
```

---

## Migrations

TAV Engine uses **Alembic** for database migrations.

### Migration Files

Located in: `backend/app/database/migrations/versions/`

**Current migrations:**
1. `001_initial.py` - Create initial tables
2. `002_rename_metadata_columns.py` - Fix reserved word conflicts
3. `003_unified_status.py` - Unified status system
4. `004_execution_metadata.py` - Add execution metadata
5. `005_add_execution_result_indexes.py` - Performance indexes
6. `006_add_workflow_fields.py` - Template system fields
7. `007_create_workflow_state.py` - Persistent state storage
8. `008_create_execution_iterations.py` - Loop tracking
9. `009_enhance_execution_results.py` - Enhanced result storage
10. `010_enhance_execution_logs.py` - Enhanced logging
11. `011_enhance_workflows_templates.py` - Template enhancements

### Running Migrations

**Automatic:**
```bash
python scripts/init_db.py
```

**Manual:**
```bash
cd backend
alembic upgrade head
```

### Check Migration Status

```bash
cd backend
alembic current
```

### Create New Migration

```bash
cd backend
alembic revision --autogenerate -m "description"
```

### Rollback Migration

```bash
cd backend
alembic downgrade -1
```

---

## Backup & Recovery

### Backup

**Simple backup (SQLite is just a file):**

```bash
# Stop the application first
cp backend/data/tav_engine.db backend/data/tav_engine.db.backup
```

**With timestamp:**
```bash
cp backend/data/tav_engine.db "backend/data/tav_engine.db.backup.$(date +%Y%m%d_%H%M%S)"
```

**Automated backup script:**
```bash
# Create backup directory
mkdir -p backend/data/backups

# Backup with timestamp
DATE=$(date +%Y%m%d_%H%M%S)
cp backend/data/tav_engine.db "backend/data/backups/tav_engine_$DATE.db"

# Keep only last 7 backups
cd backend/data/backups
ls -t tav_engine_*.db | tail -n +8 | xargs rm -f
```

### Recovery

```bash
# Stop the application
# Restore from backup
cp backend/data/tav_engine.db.backup backend/data/tav_engine.db
# Start the application
```

### Export Data (for migration)

```bash
# Export to SQL
sqlite3 backend/data/tav_engine.db .dump > backup.sql

# Restore from SQL
sqlite3 backend/data/tav_engine_new.db < backup.sql
```

---

## Performance

### Query Performance

**Indexed Queries (Fast):**
- List workflows by status
- Get executions by workflow_id
- Search workflows by name
- Get recent executions

**Unindexed Queries (Slower):**
- Full-text search in descriptions
- Complex JSON queries
- Large data scans

### Optimization Tips

1. **Regular VACUUM:**
   ```bash
   sqlite3 backend/data/tav_engine.db "VACUUM;"
   ```
   Optimizes database file, reclaims space

2. **Analyze Tables:**
   ```bash
   sqlite3 backend/data/tav_engine.db "ANALYZE;"
   ```
   Updates query planner statistics

3. **Enable WAL Mode:**
   ```bash
   sqlite3 backend/data/tav_engine.db "PRAGMA journal_mode=WAL;"
   ```
   Better concurrent read performance

4. **Regular Cleanup:**
   - Enable auto-cleanup in Settings → Storage
   - Delete old executions
   - Remove unused files

### Size Management

**Database grows with:**
- Workflow definitions (small)
- Execution history (moderate)
- Execution results (can be large)
- Execution logs (moderate)

**Typical sizes:**
- 100 workflows: ~10 MB
- 1,000 executions: ~50 MB
- 10,000 executions: ~500 MB

**Keep size manageable:**
- Set `max_execution_history` limit
- Enable `auto_cleanup`
- Set `result_storage_days`

---

## Database Utilities

### View Database Schema

```bash
python backend/scripts/visualize_tables.py
```

Shows all tables with column counts and relationships.

### Check Database Status

```bash
python backend/scripts/check_db.py
```

Shows:
- Number of workflows
- Number of executions
- Database file size
- Table row counts

### Check Stuck Executions

```bash
python backend/scripts/check_stuck_executions.py
```

Finds executions stuck in "running" state.

### Delete All Data (Reset)

```bash
python backend/scripts/delete_all_data.py
```

⚠️ **Warning:** Deletes all workflows, executions, and data!

---

## Database Access

### From Python Code

```python
from app.database.session import SessionLocal
from app.database.models.workflow import Workflow

# Create session
db = SessionLocal()

try:
    # Query workflows
    workflows = db.query(Workflow).all()
    
    # Create workflow
    new_workflow = Workflow(
        name="My Workflow",
        workflow_data={...}
    )
    db.add(new_workflow)
    db.commit()
    
finally:
    db.close()
```

### Direct SQL Access

```bash
# Open SQLite shell
sqlite3 backend/data/tav_engine.db

# List tables
.tables

# View table schema
.schema workflows

# Query data
SELECT id, name, status FROM workflows;

# Exit
.quit
```

---

## Best Practices

### For Developers

1. **Always use migrations** - Don't modify schema directly
2. **Close database sessions** - Use try/finally or context managers
3. **Use indexes** - Check execution plans for slow queries
4. **Validate data** - Use Pydantic schemas before database operations

### For Administrators

1. **Regular backups** - Automate daily backups
2. **Monitor size** - Keep database under 1GB for best performance
3. **Enable cleanup** - Prevent unlimited growth
4. **Regular maintenance** - VACUUM and ANALYZE monthly

### For Production

**Note:** For production deployments, consider Enterprise Edition with PostgreSQL support for:
- Better concurrent access
- Advanced features (full-text search, JSON operations)
- Replication and high availability
- Better performance at scale

---

## Troubleshooting

### Database Locked Errors

**Problem:** "database is locked"

**Cause:** Multiple processes accessing SQLite simultaneously

**Solution:**
- Only run ONE backend instance
- Close any database browser tools
- Ensure no background processes are using the database

### Slow Queries

**Problem:** Queries taking >1 second

**Solution:**
```bash
# Optimize database
sqlite3 backend/data/tav_engine.db "VACUUM; ANALYZE;"

# Enable WAL mode
sqlite3 backend/data/tav_engine.db "PRAGMA journal_mode=WAL;"
```

### Database Corruption

**Problem:** "database disk image is malformed"

**Solution:**
```bash
# Try to recover
sqlite3 backend/data/tav_engine.db ".recover" | sqlite3 recovered.db

# Or restore from backup
cp backend/data/tav_engine.db.backup backend/data/tav_engine.db
```

### Large Database File

**Problem:** Database file >1GB

**Solution:**
- Enable auto-cleanup
- Reduce `max_execution_history`
- Reduce `result_storage_days`
- Run VACUUM to reclaim space

---

## Related Documentation

- [Settings Structure](../configuration/settings.md) - All database-stored settings
- [Execution Architecture](executor.md) - How execution data flows
- [Node System](nodes.md) - How node data is stored

---

## Support

- 📖 [Full Documentation](../README.md)
- 🐛 [Report Issues](https://github.com/Markepattsu/tav_opensource/issues)
- 💬 [Community Discussions](https://github.com/Markepattsu/tav_opensource/discussions)
