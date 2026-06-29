"""ML Training Features - Dataset Splits, Versioning, Annotations, Augmentation

Revision ID: 002
Revises: 001
Create Date: 2024-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add dataset_split column to data_items
    op.add_column('data_items', 
        sa.Column('dataset_split', sa.String(20), server_default='unassigned', nullable=True)
    )
    op.create_index('idx_data_items_dataset_split', 'data_items', ['dataset_split'])
    
    # Add annotations JSONB column to data_items for bounding boxes, segmentation, NER, etc.
    op.add_column('data_items',
        sa.Column('annotations', postgresql.JSONB(), server_default='{}', nullable=True)
    )
    
    # Add embedding column for similarity search
    op.add_column('data_items',
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True)
    )
    
    # Add uncertainty_score for active learning
    op.add_column('data_items',
        sa.Column('uncertainty_score', sa.Float(), nullable=True)
    )
    
    # Add augmented_from for tracking augmented data
    op.add_column('data_items',
        sa.Column('augmented_from', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('data_items.id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column('data_items',
        sa.Column('augmentation_type', sa.String(100), nullable=True)
    )
    
    # Dataset Versions table
    op.create_table(
        'dataset_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('dataset_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_count', sa.Integer(), server_default='0'),
        sa.Column('train_count', sa.Integer(), server_default='0'),
        sa.Column('val_count', sa.Integer(), server_default='0'),
        sa.Column('test_count', sa.Integer(), server_default='0'),
        sa.Column('item_ids', postgresql.JSONB(), server_default='[]'),
        sa.Column('split_config', postgresql.JSONB(), server_default='{}'),
        sa.Column('statistics', postgresql.JSONB(), server_default='{}'),
        sa.Column('is_published', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('idx_dataset_versions_project_id', 'dataset_versions', ['project_id'])
    op.create_index('idx_dataset_versions_version', 'dataset_versions', ['project_id', 'version'], unique=True)
    
    # Dataset Cards table
    op.create_table(
        'dataset_cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('homepage', sa.String(500)),
        sa.Column('license', sa.String(100)),
        sa.Column('citation', sa.Text()),
        sa.Column('languages', postgresql.JSONB(), server_default='[]'),
        sa.Column('task_categories', postgresql.JSONB(), server_default='[]'),
        sa.Column('task_ids', postgresql.JSONB(), server_default='[]'),
        sa.Column('size_categories', sa.String(50)),
        sa.Column('source_datasets', postgresql.JSONB(), server_default='[]'),
        sa.Column('paperswithcode_id', sa.String(100)),
        sa.Column('annotations_creators', postgresql.JSONB(), server_default='[]'),
        sa.Column('language_creators', postgresql.JSONB(), server_default='[]'),
        sa.Column('multilinguality', sa.String(50)),
        sa.Column('pretty_name', sa.String(255)),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        sa.Column('configs', postgresql.JSONB(), server_default='[]'),
        sa.Column('bias_risks', sa.Text()),
        sa.Column('ethical_considerations', sa.Text()),
        sa.Column('curation_rationale', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Annotation Types table (for managing annotation schemas per project)
    op.create_table(
        'annotation_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('annotation_kind', sa.String(50), nullable=False),  # bbox, polygon, ner, classification, etc.
        sa.Column('schema', postgresql.JSONB(), server_default='{}'),  # JSON schema for validation
        sa.Column('color', sa.String(7), server_default='#3B82F6'),
        sa.Column('shortcut_key', sa.String(10)),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_annotation_types_project', 'annotation_types', ['project_id'])
    
    # Augmentation Rules table
    op.create_table(
        'augmentation_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False),  # text, image, audio
        sa.Column('augmentation_type', sa.String(100), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), server_default='{}'),
        sa.Column('probability', sa.Float(), server_default='1.0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_augmentation_rules_project', 'augmentation_rules', ['project_id'])
    
    # Add last_export_id to exports for incremental exports
    op.add_column('exports',
        sa.Column('base_export_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('exports.id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column('exports',
        sa.Column('is_incremental', sa.Boolean(), server_default='false')
    )
    op.add_column('exports',
        sa.Column('dataset_version_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('dataset_versions.id', ondelete='SET NULL'), nullable=True)
    )


def downgrade() -> None:
    # Drop new columns from exports
    op.drop_column('exports', 'dataset_version_id')
    op.drop_column('exports', 'is_incremental')
    op.drop_column('exports', 'base_export_id')
    
    # Drop new tables
    op.drop_table('augmentation_rules')
    op.drop_table('annotation_types')
    op.drop_table('dataset_cards')
    op.drop_table('dataset_versions')
    
    # Drop new columns from data_items
    op.drop_column('data_items', 'augmentation_type')
    op.drop_column('data_items', 'augmented_from')
    op.drop_column('data_items', 'uncertainty_score')
    op.drop_column('data_items', 'embedding')
    op.drop_column('data_items', 'annotations')
    op.drop_index('idx_data_items_dataset_split', 'data_items')
    op.drop_column('data_items', 'dataset_split')
