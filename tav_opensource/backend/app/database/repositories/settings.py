"""
Settings Repository

CRUD operations for application settings with audit trail support.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database.models.setting import Setting, SettingHistory
from app.utils.timezone import get_local_now

logger = logging.getLogger(__name__)


class SettingsRepository:
    """
    Repository for settings database operations.
    
    Provides CRUD operations with automatic audit trail logging.
    """
    
    def __init__(self, db: Session):
        """
        Initialize repository.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            namespace: Setting namespace (e.g., 'ai', 'execution')
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value (parsed from JSON) or default
        """
        try:
            setting = self.db.query(Setting).filter(
                and_(Setting.namespace == namespace, Setting.key == key)
            ).first()
            
            if not setting:
                return default
            
            # Parse JSON value
            try:
                return json.loads(setting.value)
            except (json.JSONDecodeError, TypeError):
                return setting.value
                
        except Exception as e:
            logger.error(f"Error getting setting {namespace}.{key}: {e}")
            return default
    
    def set(
        self, 
        namespace: str, 
        key: str, 
        value: Any, 
        updated_by: str = "system",
        description: Optional[str] = None
    ) -> bool:
        """
        Set a setting value with audit trail.
        
        Args:
            namespace: Setting namespace
            key: Setting key
            value: Setting value (will be JSON-encoded)
            updated_by: Who is making the change
            description: Optional description of the setting
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get old value for audit trail
            old_setting = self.db.query(Setting).filter(
                and_(Setting.namespace == namespace, Setting.key == key)
            ).first()
            
            old_value = None
            if old_setting:
                old_value = old_setting.value
            
            # Encode new value as JSON
            new_value_json = json.dumps(value, default=str, ensure_ascii=False)
            
            # Check if value actually changed
            if old_value == new_value_json:
                logger.debug(f"Setting {namespace}.{key} unchanged, skipping update")
                return True
            
            # Create or update setting
            if old_setting:
                old_setting.value = new_value_json
                old_setting.updated_by = updated_by
                old_setting.updated_at = get_local_now()
                if description:
                    old_setting.description = description
            else:
                new_setting = Setting(
                    namespace=namespace,
                    key=key,
                    value=new_value_json,
                    updated_by=updated_by,
                    description=description
                )
                self.db.add(new_setting)
            
            # Add audit trail entry
            history_entry = SettingHistory(
                namespace=namespace,
                key=key,
                old_value=old_value,
                new_value=new_value_json,
                changed_by=updated_by,
                changed_at=get_local_now()
            )
            self.db.add(history_entry)
            
            # Commit transaction
            self.db.commit()
            
            logger.info(f"Updated setting {namespace}.{key} (by: {updated_by})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting {namespace}.{key}: {e}")
            self.db.rollback()
            return False
    
    def delete(self, namespace: str, key: str, deleted_by: str = "system") -> bool:
        """
        Delete a setting with audit trail.
        
        Args:
            namespace: Setting namespace
            key: Setting key
            deleted_by: Who is deleting the setting
            
        Returns:
            True if successful, False otherwise
        """
        try:
            setting = self.db.query(Setting).filter(
                and_(Setting.namespace == namespace, Setting.key == key)
            ).first()
            
            if not setting:
                logger.warning(f"Setting {namespace}.{key} not found for deletion")
                return False
            
            old_value = setting.value
            
            # Delete setting
            self.db.delete(setting)
            
            # Add audit trail entry
            history_entry = SettingHistory(
                namespace=namespace,
                key=key,
                old_value=old_value,
                new_value=None,  # NULL indicates deletion
                changed_by=deleted_by,
                changed_at=get_local_now()
            )
            self.db.add(history_entry)
            
            # Commit transaction
            self.db.commit()
            
            logger.info(f"Deleted setting {namespace}.{key} (by: {deleted_by})")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting {namespace}.{key}: {e}")
            self.db.rollback()
            return False
    
    def get_all(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all settings, optionally filtered by namespace.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            Dictionary of all settings (parsed from JSON)
        """
        try:
            query = self.db.query(Setting)
            
            if namespace:
                query = query.filter(Setting.namespace == namespace)
            
            settings = query.all()
            
            result = {}
            for setting in settings:
                # Create nested dict structure
                if setting.namespace not in result:
                    result[setting.namespace] = {}
                
                try:
                    result[setting.namespace][setting.key] = json.loads(setting.value)
                except (json.JSONDecodeError, TypeError):
                    result[setting.namespace][setting.key] = setting.value
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        """
        Get all settings in a specific namespace.
        
        Args:
            namespace: Namespace to retrieve
            
        Returns:
            Dictionary of settings in namespace
        """
        try:
            settings = self.db.query(Setting).filter(
                Setting.namespace == namespace
            ).all()
            
            result = {}
            for setting in settings:
                try:
                    result[setting.key] = json.loads(setting.value)
                except (json.JSONDecodeError, TypeError):
                    result[setting.key] = setting.value
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting namespace {namespace}: {e}")
            return {}
    
    def clear_namespace(self, namespace: str, deleted_by: str = "system") -> bool:
        """
        Delete all settings in a namespace.
        
        Args:
            namespace: Namespace to clear
            deleted_by: Who is clearing the namespace
            
        Returns:
            True if successful, False otherwise
        """
        try:
            settings = self.db.query(Setting).filter(
                Setting.namespace == namespace
            ).all()
            
            for setting in settings:
                # Add audit trail for each deletion
                history_entry = SettingHistory(
                    namespace=setting.namespace,
                    key=setting.key,
                    old_value=setting.value,
                    new_value=None,
                    changed_by=deleted_by,
                    changed_at=get_local_now()
                )
                self.db.add(history_entry)
                
                # Delete setting
                self.db.delete(setting)
            
            self.db.commit()
            
            logger.info(f"Cleared namespace {namespace} ({len(settings)} settings, by: {deleted_by})")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing namespace {namespace}: {e}")
            self.db.rollback()
            return False
    
    def bulk_set(
        self, 
        settings: Dict[str, Dict[str, Any]], 
        updated_by: str = "system"
    ) -> int:
        """
        Set multiple settings at once.
        
        Args:
            settings: Nested dict {namespace: {key: value}}
            updated_by: Who is making the changes
            
        Returns:
            Number of settings actually changed
        """
        changed_count = 0
        
        try:
            for namespace, namespace_settings in settings.items():
                for key, value in namespace_settings.items():
                    if self.set(namespace, key, value, updated_by):
                        changed_count += 1
            
            return changed_count
            
        except Exception as e:
            logger.error(f"Error in bulk_set: {e}")
            return changed_count
    
    def get_history(
        self, 
        namespace: Optional[str] = None,
        key: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get setting change history.
        
        Args:
            namespace: Optional namespace filter
            key: Optional key filter
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries
        """
        try:
            query = self.db.query(SettingHistory)
            
            if namespace and key:
                query = query.filter(
                    and_(
                        SettingHistory.namespace == namespace,
                        SettingHistory.key == key
                    )
                )
            elif namespace:
                query = query.filter(SettingHistory.namespace == namespace)
            
            query = query.order_by(SettingHistory.changed_at.desc()).limit(limit)
            
            history = query.all()
            
            return [
                {
                    "namespace": entry.namespace,
                    "key": entry.key,
                    "old_value": entry.old_value,
                    "new_value": entry.new_value,
                    "changed_at": entry.changed_at,
                    "changed_by": entry.changed_by,
                    "change_reason": entry.change_reason
                }
                for entry in history
            ]
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def exists(self, namespace: str, key: str) -> bool:
        """
        Check if a setting exists.
        
        Args:
            namespace: Setting namespace
            key: Setting key
            
        Returns:
            True if setting exists
        """
        try:
            count = self.db.query(Setting).filter(
                and_(Setting.namespace == namespace, Setting.key == key)
            ).count()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking existence of {namespace}.{key}: {e}")
            return False

