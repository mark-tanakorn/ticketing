"""
User Model

User authentication and authorization with comprehensive employee information.
"""

from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Index, Integer, DECIMAL, Text
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy import String as SQLString

from app.database.base import Base, get_current_timestamp


class User(Base):
    """
    User model with comprehensive employee and user management information.
    
    This structure supports full HR integration with authentication,
    authorization, and employee lifecycle management.
    """
    __tablename__ = "users"

    # Primary key (auto-incrementing integer)
    # SQLite: INTEGER PRIMARY KEY (64-bit)
    # PostgreSQL: BIGINT/SERIAL
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    
    # Unique identifier (UUID for external references)
    user_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys to related systems
    agent_id = Column(Integer, nullable=True, index=True)
    company_id = Column(Integer, nullable=True, index=True)
    
    # Personal identification
    user_nric = Column(String(15), nullable=True)  # National registration/identity number (NRIC format)
    user_name = Column(String(256), unique=True, nullable=False, index=True)  # Username for login (UNIQUE)
    user_initial = Column(String(10), nullable=True)
    user_password = Column(String(500), nullable=True)  # Hashed password (nullable per spec, but should be set for active users)
    user_email = Column(String(255), nullable=True, index=True)  # Keep 255 for modern email addresses
    
    # Name fields
    user_firstname = Column(String(50), nullable=True)
    user_lastname = Column(String(50), nullable=True)
    
    # Personal information
    user_gender = Column(String(7), nullable=True)  # M/F/Other
    user_maritalstatus = Column(String(10), nullable=True)  # Single/Married/etc.
    
    # Organization structure
    user_department_id = Column(Integer, nullable=True, index=True)
    user_branch_id = Column(Integer, nullable=True, index=True)
    
    # Contact information
    user_officephone = Column(String(50), nullable=True)
    user_homephone = Column(String(50), nullable=True)
    user_handphone = Column(String(50), nullable=True)
    
    # Address fields
    user_address1 = Column(String(150), nullable=True)
    user_address2 = Column(String(150), nullable=True)
    user_addresscity = Column(String(50), nullable=True)
    user_stateprovince = Column(String(50), nullable=True)
    user_postalcode = Column(String(10), nullable=True)
    user_citycode = Column(String(5), nullable=True)
    user_countrycode = Column(String(3), nullable=True)  # ISO 3166-1 alpha-3 (e.g., USA, SGP)
    
    # Notes and metadata
    user_note = Column(Text, nullable=True)
    
    # Status flags (per spec: nullable=True, but we provide defaults)
    user_is_deleted = Column(Boolean, default=False, nullable=True, index=True)
    user_is_disabled = Column(Boolean, default=False, nullable=True, index=True)
    is_show = Column(Boolean, default=True, nullable=True)
    is_update = Column(Boolean, default=False, nullable=True)
    is_ad_user = Column(Boolean, default=False, nullable=True)
    
    # Registration and timestamps
    user_register_on = Column(DateTime(timezone=True), nullable=True)
    user_created_by = Column(String(255), nullable=True)
    user_created_on = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    user_modified_by = Column(String(255), nullable=True)
    user_modified_on = Column(DateTime(timezone=True), default=get_current_timestamp, onupdate=get_current_timestamp, nullable=True)
    
    # File paths for photos and signatures (keep longer for cloud storage URLs)
    user_photo_path = Column(String(1000), nullable=True)
    user_signature_path = Column(String(1000), nullable=True)
    
    # Security
    user_is_firsttime_login = Column(Boolean, default=True, nullable=True)
    user_security_question_id = Column(Integer, nullable=True)
    user_security_answer = Column(String(256), nullable=True)
    user_is_trustedhub = Column(Boolean, default=False, nullable=True)
    
    # Employee information
    user_staffcode = Column(String(50), nullable=True, index=True)
    user_employee_id = Column(String(30), nullable=True, index=True)
    user_employee_number = Column(String(256), nullable=True, index=True)
    job_title = Column(String(512), nullable=True)
    staff_type = Column(String(50), nullable=True)
    highest_education = Column(String(512), nullable=True)
    join_date = Column(DateTime(timezone=True), nullable=True)
    
    # Approval limits
    user_approval_limit = Column(DECIMAL(18, 2), nullable=True)
    user_deviation_limit = Column(DECIMAL(18, 2), nullable=True)
    
    # Hierarchy and relationships
    supervisor_user_id = Column(Integer, nullable=True, index=True)
    backup_user_id = Column(Integer, nullable=True, index=True)
    
    # Notifications
    user_notification_emails = Column(String(512), nullable=True)  # Match spec: nvarchar(512)
    
    # Lifecycle tracking
    user_deleted_by = Column(String(255), nullable=True)
    user_deleted_on = Column(DateTime(timezone=True), nullable=True)
    user_reset_password_by = Column(String(255), nullable=True)
    user_reset_password_on = Column(DateTime(timezone=True), nullable=True)
    user_disabled_by = Column(String(255), nullable=True)
    user_disabled_on = Column(DateTime(timezone=True), nullable=True)
    user_enabled_by = Column(String(255), nullable=True)
    user_enabled_on = Column(DateTime(timezone=True), nullable=True)
    user_change_password_by = Column(String(255), nullable=True)
    user_change_password_on = Column(DateTime(timezone=True), nullable=True)
    
    # RO fields (possibly for reporting organization or similar)
    ro1 = Column(Integer, nullable=True)
    ro2 = Column(Integer, nullable=True)
    
    # Concurrency control
    editing_by = Column(String(50), nullable=True)  # Match spec: nvarchar(50)
    version_no = Column(Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_users_user_id', 'user_id'),
        Index('idx_users_user_name', 'user_name'),
        Index('idx_users_user_email', 'user_email'),
        Index('idx_users_user_staffcode', 'user_staffcode'),
        Index('idx_users_user_employee_id', 'user_employee_id'),
        Index('idx_users_user_employee_number', 'user_employee_number'),
        Index('idx_users_user_is_deleted', 'user_is_deleted'),
        Index('idx_users_user_is_disabled', 'user_is_disabled'),
        Index('idx_users_agent_id', 'agent_id'),
        Index('idx_users_company_id', 'company_id'),
        Index('idx_users_user_department_id', 'user_department_id'),
        Index('idx_users_user_branch_id', 'user_branch_id'),
        Index('idx_users_supervisor_user_id', 'supervisor_user_id'),
        Index('idx_users_backup_user_id', 'backup_user_id'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, user_id='{self.user_id}', user_name='{self.user_name}', user_email='{self.user_email}')>"
