"""Add custom node builder conversations

Revision ID: 012_custom_node_conversations
Revises: 011_enhance_workflows_templates
Create Date: 2025-12-08

Adds support for conversational AI-powered custom node generation:
- conversations: Tracks AI chat sessions for node building
- conversation_messages: Full message history per conversation
- custom_nodes: Successfully generated and saved custom nodes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012_custom_node_conversations'
down_revision = '011_enhance_workflows_templates'
branch_labels = None
depends_on = None


def upgrade():
    """Create custom node builder tables"""
    
    # 1. Create conversations table (without FK to custom_nodes yet)
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(length=36), nullable=False, comment='UUID conversation ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User who owns this conversation'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='Conversation title'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Conversation status'),
        sa.Column('provider', sa.String(length=50), nullable=False, comment='AI provider (openai, anthropic, etc.)'),
        sa.Column('model', sa.String(length=100), nullable=False, comment='AI model name'),
        sa.Column('temperature', sa.String(length=10), nullable=True, comment='Generation temperature'),
        sa.Column('requirements', sa.JSON(), nullable=True, comment='Extracted requirements JSON'),
        sa.Column('generated_code', sa.Text(), nullable=True, comment='Generated Python code'),
        sa.Column('node_type', sa.String(length=100), nullable=True, comment='Node type identifier'),
        sa.Column('class_name', sa.String(length=100), nullable=True, comment='Generated class name'),
        sa.Column('validation_status', sa.String(length=50), nullable=True, comment='Validation status'),
        sa.Column('validation_errors', sa.JSON(), nullable=True, comment='Validation errors list'),
        sa.Column('custom_node_id', sa.Integer(), nullable=True, comment='Link to saved custom node'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='Last update timestamp'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='Completion timestamp'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_conversation_user'),
        # Note: FK to custom_nodes omitted for SQLite compatibility
        # The relationship exists at the ORM level but not enforced at DB level
    )
    
    # Indexes for conversations
    op.create_index('idx_conversation_user_status', 'conversations', ['user_id', 'status'])
    op.create_index('idx_conversation_user_created', 'conversations', ['user_id', 'created_at'])
    op.create_index('idx_conversation_status_updated', 'conversations', ['status', 'updated_at'])
    op.create_index('idx_conversation_title', 'conversations', ['title'])
    op.create_index('idx_conversation_created_at', 'conversations', ['created_at'])
    
    
    # 2. Create conversation_messages table
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='Message ID'),
        sa.Column('conversation_id', sa.String(length=36), nullable=False, comment='Parent conversation'),
        sa.Column('role', sa.String(length=20), nullable=False, comment='Message role: user, assistant, system'),
        sa.Column('content', sa.Text(), nullable=False, comment='Message content'),
        sa.Column('provider', sa.String(length=50), nullable=True, comment='AI provider used'),
        sa.Column('model', sa.String(length=100), nullable=True, comment='AI model used'),
        sa.Column('tokens_used', sa.Integer(), nullable=True, comment='Token count'),
        sa.Column('response_time_ms', sa.Integer(), nullable=True, comment='Response time in milliseconds'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Message timestamp'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], 
                               name='fk_message_conversation', ondelete='CASCADE'),
    )
    
    # Indexes for messages
    op.create_index('idx_conversation_message_conversation_id', 'conversation_messages', ['conversation_id'])
    op.create_index('idx_conversation_message_conversation_created', 'conversation_messages', ['conversation_id', 'created_at'])
    op.create_index('idx_conversation_message_role', 'conversation_messages', ['role'])
    op.create_index('idx_conversation_message_created_at', 'conversation_messages', ['created_at'])
    
    
    # 3. Create custom_nodes table
    op.create_table(
        'custom_nodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User who created this node'),
        sa.Column('conversation_id', sa.String(length=36), nullable=True, comment='Source conversation'),
        sa.Column('node_type', sa.String(length=100), nullable=False, comment='Unique node type identifier'),
        sa.Column('display_name', sa.String(length=255), nullable=False, comment='Human-readable name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Node description'),
        sa.Column('category', sa.String(length=50), nullable=False, comment='Node category'),
        sa.Column('icon', sa.String(length=100), nullable=True, comment='FontAwesome icon class'),
        sa.Column('code', sa.Text(), nullable=False, comment='Complete Python node code'),
        sa.Column('file_path', sa.String(length=500), nullable=True, comment='Filesystem path'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='Active status'),
        sa.Column('is_registered', sa.Boolean(), nullable=False, default=False, comment='Registry status'),
        sa.Column('version', sa.String(length=20), nullable=True, comment='Node version'),
        sa.Column('input_ports', sa.JSON(), nullable=True, comment='Cached input port definitions'),
        sa.Column('output_ports', sa.JSON(), nullable=True, comment='Cached output port definitions'),
        sa.Column('config_schema', sa.JSON(), nullable=True, comment='Cached config schema'),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0, comment='Usage statistics'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='Last update timestamp'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='Last usage timestamp'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('node_type', name='uq_custom_node_type'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_custom_node_user'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name='fk_custom_node_conversation'),
    )
    
    # Indexes for custom_nodes
    op.create_index('idx_custom_node_user_active', 'custom_nodes', ['user_id', 'is_active'])
    op.create_index('idx_custom_node_category', 'custom_nodes', ['category'])
    op.create_index('idx_custom_node_created', 'custom_nodes', ['created_at'])
    op.create_index('idx_custom_node_node_type', 'custom_nodes', ['node_type'])
    op.create_index('idx_custom_node_is_active', 'custom_nodes', ['is_active'])


def downgrade():
    """Drop custom node builder tables"""
    
    # Drop custom_nodes table
    op.drop_index('idx_custom_node_is_active', table_name='custom_nodes')
    op.drop_index('idx_custom_node_node_type', table_name='custom_nodes')
    op.drop_index('idx_custom_node_created', table_name='custom_nodes')
    op.drop_index('idx_custom_node_category', table_name='custom_nodes')
    op.drop_index('idx_custom_node_user_active', table_name='custom_nodes')
    op.drop_table('custom_nodes')
    
    # Drop conversation_messages table
    op.drop_index('idx_conversation_message_created_at', table_name='conversation_messages')
    op.drop_index('idx_conversation_message_role', table_name='conversation_messages')
    op.drop_index('idx_conversation_message_conversation_created', table_name='conversation_messages')
    op.drop_index('idx_conversation_message_conversation_id', table_name='conversation_messages')
    op.drop_table('conversation_messages')
    
    # Drop conversations table
    op.drop_index('idx_conversation_created_at', table_name='conversations')
    op.drop_index('idx_conversation_title', table_name='conversations')
    op.drop_index('idx_conversation_status_updated', table_name='conversations')
    op.drop_index('idx_conversation_user_created', table_name='conversations')
    op.drop_index('idx_conversation_user_status', table_name='conversations')
    op.drop_table('conversations')

