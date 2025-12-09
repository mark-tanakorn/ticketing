"""
User Schemas

Pydantic models for user data validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    user_name: str = Field(..., max_length=255, description="Username for login")
    user_email: Optional[EmailStr] = Field(None, max_length=255, description="User email address")
    user_firstname: Optional[str] = Field(None, max_length=255, description="First name")
    user_lastname: Optional[str] = Field(None, max_length=255, description="Last name")
    

class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    user_password: str = Field(..., min_length=8, max_length=500, description="User password (will be hashed)")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    company_id: Optional[int] = Field(None, description="Company ID")
    user_nric: Optional[str] = Field(None, max_length=50, description="National registration/identity number")
    user_initial: Optional[str] = Field(None, max_length=10, description="User initials")
    user_gender: Optional[str] = Field(None, max_length=20, description="Gender")
    user_maritalstatus: Optional[str] = Field(None, max_length=50, description="Marital status")
    user_department_id: Optional[int] = Field(None, description="Department ID")
    user_branch_id: Optional[int] = Field(None, description="Branch ID")
    user_officephone: Optional[str] = Field(None, max_length=50, description="Office phone")
    user_homephone: Optional[str] = Field(None, max_length=50, description="Home phone")
    user_handphone: Optional[str] = Field(None, max_length=50, description="Mobile phone")
    user_address1: Optional[str] = Field(None, max_length=500, description="Address line 1")
    user_address2: Optional[str] = Field(None, max_length=500, description="Address line 2")
    user_addresscity: Optional[str] = Field(None, max_length=100, description="City")
    user_stateprovince: Optional[str] = Field(None, max_length=100, description="State/Province")
    user_postalcode: Optional[str] = Field(None, max_length=20, description="Postal code")
    user_citycode: Optional[str] = Field(None, max_length=20, description="City code")
    user_countrycode: Optional[str] = Field(None, max_length=20, description="Country code")
    user_note: Optional[str] = Field(None, description="Additional notes")
    user_staffcode: Optional[str] = Field(None, max_length=50, description="Staff code")
    user_employee_id: Optional[str] = Field(None, max_length=50, description="Employee ID")
    user_employee_number: Optional[str] = Field(None, max_length=50, description="Employee number")
    job_title: Optional[str] = Field(None, max_length=255, description="Job title")
    staff_type: Optional[str] = Field(None, max_length=100, description="Staff type")
    highest_education: Optional[str] = Field(None, max_length=255, description="Highest education level")
    join_date: Optional[datetime] = Field(None, description="Date joined the organization")
    user_approval_limit: Optional[Decimal] = Field(None, description="Approval limit")
    user_deviation_limit: Optional[Decimal] = Field(None, description="Deviation limit")
    supervisor_user_id: Optional[int] = Field(None, description="Supervisor user ID")
    backup_user_id: Optional[int] = Field(None, description="Backup user ID")
    user_notification_emails: Optional[str] = Field(None, description="Notification email addresses")
    

class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    
    user_name: Optional[str] = Field(None, max_length=255, description="Username for login")
    user_password: Optional[str] = Field(None, min_length=8, max_length=500, description="User password (will be hashed)")
    user_email: Optional[EmailStr] = Field(None, max_length=255, description="User email address")
    user_firstname: Optional[str] = Field(None, max_length=255, description="First name")
    user_lastname: Optional[str] = Field(None, max_length=255, description="Last name")
    agent_id: Optional[int] = Field(None, description="Agent ID")
    company_id: Optional[int] = Field(None, description="Company ID")
    user_nric: Optional[str] = Field(None, max_length=50, description="National registration/identity number")
    user_initial: Optional[str] = Field(None, max_length=10, description="User initials")
    user_gender: Optional[str] = Field(None, max_length=20, description="Gender")
    user_maritalstatus: Optional[str] = Field(None, max_length=50, description="Marital status")
    user_department_id: Optional[int] = Field(None, description="Department ID")
    user_branch_id: Optional[int] = Field(None, description="Branch ID")
    user_officephone: Optional[str] = Field(None, max_length=50, description="Office phone")
    user_homephone: Optional[str] = Field(None, max_length=50, description="Home phone")
    user_handphone: Optional[str] = Field(None, max_length=50, description="Mobile phone")
    user_address1: Optional[str] = Field(None, max_length=500, description="Address line 1")
    user_address2: Optional[str] = Field(None, max_length=500, description="Address line 2")
    user_addresscity: Optional[str] = Field(None, max_length=100, description="City")
    user_stateprovince: Optional[str] = Field(None, max_length=100, description="State/Province")
    user_postalcode: Optional[str] = Field(None, max_length=20, description="Postal code")
    user_citycode: Optional[str] = Field(None, max_length=20, description="City code")
    user_countrycode: Optional[str] = Field(None, max_length=20, description="Country code")
    user_note: Optional[str] = Field(None, description="Additional notes")
    user_is_disabled: Optional[bool] = Field(None, description="Whether user is disabled")
    user_staffcode: Optional[str] = Field(None, max_length=50, description="Staff code")
    user_employee_id: Optional[str] = Field(None, max_length=50, description="Employee ID")
    user_employee_number: Optional[str] = Field(None, max_length=50, description="Employee number")
    job_title: Optional[str] = Field(None, max_length=255, description="Job title")
    staff_type: Optional[str] = Field(None, max_length=100, description="Staff type")
    highest_education: Optional[str] = Field(None, max_length=255, description="Highest education level")
    join_date: Optional[datetime] = Field(None, description="Date joined the organization")
    user_approval_limit: Optional[Decimal] = Field(None, description="Approval limit")
    user_deviation_limit: Optional[Decimal] = Field(None, description="Deviation limit")
    supervisor_user_id: Optional[int] = Field(None, description="Supervisor user ID")
    backup_user_id: Optional[int] = Field(None, description="Backup user ID")
    user_notification_emails: Optional[str] = Field(None, description="Notification email addresses")
    user_modified_by: Optional[str] = Field(None, max_length=255, description="Modified by username")


class UserInDB(UserBase):
    """Schema for user as stored in database."""
    
    id: int = Field(..., description="Primary key")
    user_id: str = Field(..., max_length=36, description="UUID for external references")
    agent_id: Optional[int] = None
    company_id: Optional[int] = None
    user_nric: Optional[str] = None
    user_initial: Optional[str] = None
    user_gender: Optional[str] = None
    user_maritalstatus: Optional[str] = None
    user_department_id: Optional[int] = None
    user_branch_id: Optional[int] = None
    user_officephone: Optional[str] = None
    user_homephone: Optional[str] = None
    user_handphone: Optional[str] = None
    user_address1: Optional[str] = None
    user_address2: Optional[str] = None
    user_addresscity: Optional[str] = None
    user_stateprovince: Optional[str] = None
    user_postalcode: Optional[str] = None
    user_citycode: Optional[str] = None
    user_countrycode: Optional[str] = None
    user_note: Optional[str] = None
    user_is_deleted: bool = False
    user_is_disabled: bool = False
    is_show: bool = True
    is_update: bool = False
    is_ad_user: bool = False
    user_register_on: Optional[datetime] = None
    user_created_by: Optional[str] = None
    user_created_on: datetime
    user_modified_by: Optional[str] = None
    user_modified_on: Optional[datetime] = None
    user_photo_path: Optional[str] = None
    user_signature_path: Optional[str] = None
    user_is_firsttime_login: bool = True
    user_security_question_id: Optional[int] = None
    user_security_answer: Optional[str] = None
    user_is_trustedhub: bool = False
    user_staffcode: Optional[str] = None
    user_employee_id: Optional[str] = None
    user_employee_number: Optional[str] = None
    job_title: Optional[str] = None
    staff_type: Optional[str] = None
    highest_education: Optional[str] = None
    join_date: Optional[datetime] = None
    user_approval_limit: Optional[Decimal] = None
    user_deviation_limit: Optional[Decimal] = None
    supervisor_user_id: Optional[int] = None
    backup_user_id: Optional[int] = None
    user_notification_emails: Optional[str] = None
    user_deleted_by: Optional[str] = None
    user_deleted_on: Optional[datetime] = None
    user_reset_password_by: Optional[str] = None
    user_reset_password_on: Optional[datetime] = None
    user_disabled_by: Optional[str] = None
    user_disabled_on: Optional[datetime] = None
    user_enabled_by: Optional[str] = None
    user_enabled_on: Optional[datetime] = None
    user_change_password_by: Optional[str] = None
    user_change_password_on: Optional[datetime] = None
    ro1: Optional[int] = None
    ro2: Optional[int] = None
    editing_by: Optional[str] = None
    version_no: int = 0
    
    class Config:
        from_attributes = True
        

class UserResponse(UserBase):
    """Schema for user response (excludes sensitive fields)."""
    
    id: int = Field(..., description="Primary key")
    user_id: str = Field(..., description="UUID for external references")
    user_staffcode: Optional[str] = None
    user_employee_id: Optional[str] = None
    user_employee_number: Optional[str] = None
    job_title: Optional[str] = None
    staff_type: Optional[str] = None
    user_department_id: Optional[int] = None
    user_branch_id: Optional[int] = None
    company_id: Optional[int] = None
    user_is_disabled: bool = False
    user_is_deleted: bool = False
    user_created_on: datetime
    user_modified_on: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    
    total: int = Field(..., description="Total number of users")
    users: list[UserResponse] = Field(..., description="List of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    

class PasswordChange(BaseModel):
    """Schema for password change request."""
    
    old_password: str = Field(..., min_length=8, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=500, description="New password")
    
    @validator('new_password')
    def passwords_must_differ(cls, v, values):
        if 'old_password' in values and v == values['old_password']:
            raise ValueError('New password must be different from old password')
        return v


class PasswordReset(BaseModel):
    """Schema for password reset by admin."""
    
    new_password: str = Field(..., min_length=8, max_length=500, description="New password")
    reset_by: str = Field(..., max_length=255, description="Username of admin resetting password")

