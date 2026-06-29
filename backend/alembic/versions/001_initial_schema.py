"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.String(50), server_default='user'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('settings', postgresql.JSONB(), server_default='{}'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_projects_user_id', 'projects', ['user_id'])
    
    # Scraping Jobs table
    op.create_table(
        'scraping_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('schedule', sa.String(100)),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('priority', sa.Integer(), server_default='0'),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('max_retries', sa.Integer(), server_default='3'),
        sa.Column('last_run', sa.DateTime(timezone=True)),
        sa.Column('next_run', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_scraping_jobs_project_id', 'scraping_jobs', ['project_id'])
    op.create_index('idx_scraping_jobs_status', 'scraping_jobs', ['status'])
    
    # Data Items table
    op.create_table(
        'data_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scraping_jobs.id', ondelete='SET NULL')),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('source_url', sa.Text()),
        sa.Column('content', sa.Text()),
        sa.Column('file_path', sa.String(500)),
        sa.Column('file_size', sa.BigInteger()),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('labels', postgresql.JSONB(), server_default='[]'),
        sa.Column('quality_score', sa.Float()),
        sa.Column('is_processed', sa.Boolean(), server_default='false'),
        sa.Column('is_labeled', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_data_items_project_id', 'data_items', ['project_id'])
    op.create_index('idx_data_items_job_id', 'data_items', ['job_id'])
    op.create_index('idx_data_items_data_type', 'data_items', ['data_type'])
    op.create_index('idx_data_items_is_labeled', 'data_items', ['is_labeled'])
    
    # Label Categories table
    op.create_table(
        'label_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('color', sa.String(7), server_default='#3B82F6'),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Exports table
    op.create_table(
        'exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('format', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500)),
        sa.Column('file_size', sa.BigInteger()),
        sa.Column('record_count', sa.Integer()),
        sa.Column('filters', postgresql.JSONB(), server_default='{}'),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
    )
    op.create_index('idx_exports_project_id', 'exports', ['project_id'])
    
    # Job Logs table
    op.create_table(
        'job_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scraping_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_job_logs_job_id', 'job_logs', ['job_id'])


def downgrade() -> None:
    op.drop_table('job_logs')
    op.drop_table('exports')
    op.drop_table('label_categories')
    op.drop_table('data_items')
    op.drop_table('scraping_jobs')
    op.drop_table('projects')
    op.drop_table('api_keys')
    op.drop_table('users')

