"""
Settings API endpoints for managing application configuration.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from database import get_db_connection


# Settings service functions (moved here to match codebase pattern)
class SettingsService:
    """Service for managing application settings stored in database."""

    @staticmethod
    def get_setting(key: str, default: Any = None) -> Any:
        """
        Get a setting value from database.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value converted to appropriate type, or default if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT value, data_type FROM settings WHERE key = %s", (key,)
            )

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                value, data_type = result
                return SettingsService._convert_value(value, data_type)

        except Exception as e:
            print(f"Error fetching setting {key}: {e}")

        # No fallback to environment variable - settings are database-only
        return default

    @staticmethod
    def set_setting(
        key: str, value: Any, description: str = "", category: str = "general"
    ) -> bool:
        """
        Set or update a setting value in database.

        Args:
            key: Setting key
            value: Setting value
            description: Human-readable description
            category: Setting category

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Determine data type
            data_type = SettingsService._infer_data_type(value)

            # Insert or update
            cursor.execute(
                """
                INSERT INTO settings (key, value, description, category, data_type, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    data_type = EXCLUDED.data_type,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, str(value), description, category, data_type),
            )

            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            print(f"Error setting {key}: {e}")
            return False

    @staticmethod
    def get_all_settings() -> dict:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of all settings with their values
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT key, value, description, category, data_type FROM settings ORDER BY category, key"
            )

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            settings = {}
            for key, value, description, category, data_type in results:
                settings[key] = {
                    "value": SettingsService._convert_value(value, data_type),
                    "description": description,
                    "category": category,
                    "data_type": data_type,
                }

            return settings

        except Exception as e:
            print(f"Error fetching all settings: {e}")
            return {}

    @staticmethod
    def _convert_value(value: str, data_type: str) -> Any:
        """Convert string value to appropriate Python type."""
        if data_type == "number":
            try:
                # Try int first, then float
                if "." in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                return float(value)  # fallback to float
        elif data_type == "boolean":
            return value.lower() in ("true", "1", "yes", "on")
        else:
            return value

    @staticmethod
    def _infer_data_type(value: Any) -> str:
        """Infer data type from value."""
        if isinstance(value, (int, float)):
            return "number"
        elif isinstance(value, bool):
            return "boolean"
        else:
            return "string"


# Convenience functions for backward compatibility
def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    return SettingsService.get_setting(key, default)


def set_setting(
    key: str, value: Any, description: str = "", category: str = "general"
) -> bool:
    """Set a setting value."""
    return SettingsService.set_setting(key, value, description, category)


def get_all_settings() -> dict:
    """Get all settings."""
    return SettingsService.get_all_settings()


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/")
async def get_settings() -> Dict[str, Any]:
    """
    Get all application settings.

    Returns:
        Dictionary of all settings with their metadata
    """
    try:
        settings = get_all_settings()
        return {"settings": settings, "count": len(settings)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch settings: {str(e)}"
        )


@router.get("/{key}")
async def get_setting_by_key(key: str) -> Dict[str, Any]:
    """
    Get a specific setting by key.

    Args:
        key: Setting key

    Returns:
        Setting information
    """
    try:
        # Get from database only
        settings = get_all_settings()
        if key in settings:
            return settings[key]

        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch setting: {str(e)}"
        )


@router.put("/{key}")
async def update_setting(key: str, payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Update a specific setting.

    Args:
        key: Setting key
        payload: Must contain 'value', optionally 'description' and 'category'

    Returns:
        Success message
    """
    try:
        if "value" not in payload:
            raise HTTPException(status_code=400, detail="Value is required")

        value = payload["value"]
        description = payload.get("description", "")
        category = payload.get("category", "general")

        success = set_setting(key, value, description, category)

        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to update setting '{key}'"
            )

        return {"message": f"Setting '{key}' updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update setting: {str(e)}"
        )


@router.post("/bulk")
async def update_settings_bulk(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Update multiple settings at once.

    Args:
        payload: Dictionary of settings to update, where keys are setting keys
                 and values are objects with 'value', 'description', 'category'

    Returns:
        Success message
    """
    try:
        updated_count = 0
        failed_keys = []

        for key, setting_data in payload.items():
            if not isinstance(setting_data, dict) or "value" not in setting_data:
                failed_keys.append(key)
                continue

            value = setting_data["value"]
            description = setting_data.get("description", "")
            category = setting_data.get("category", "general")

            success = set_setting(key, value, description, category)
            if success:
                updated_count += 1
            else:
                failed_keys.append(key)

        if failed_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to update settings: {', '.join(failed_keys)}",
            )

        return {"message": f"Successfully updated {updated_count} settings"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update settings: {str(e)}"
        )
