"""Initial schema with all tables

Revision ID: 20250314_initial
Revises:
Create Date: 2025-03-14 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '1_create_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # ### Создание таблицы tenders ###
    op.create_table(
        'tenders',
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('notification_number', sa.String(), nullable=True),
        sa.Column('notification_type', sa.String(), nullable=True),
        sa.Column('organizer', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('initial_price', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('application_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('etp_code', sa.String(), nullable=True),
        sa.Column('etp_name', sa.String(), nullable=True),
        sa.Column('etp_url', sa.String(), nullable=True),
        sa.Column('kontur_link', sa.String(), nullable=True),
        sa.Column('publication_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_modified', sa.DateTime(timezone=True), nullable=True),
        sa.Column('selection_method', sa.String(), nullable=True),
        sa.Column('smp', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='new', nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('state', sa.String(), nullable=False, server_default='RECEIVED'),
        sa.PrimaryKeyConstraint('external_id'),
        sa.Index('ix_tenders_external_id', 'external_id')
    )

    # ### Создание таблицы documents ###
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tender_id', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('storage_location', sa.String(), server_default='s3', nullable=True),
        sa.Column('status', sa.String(), server_default='pending', nullable=True),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.external_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tender_id', 'file_name', name='uq_tender_file'),
        sa.Index('ix_documents_id', 'id'),
        sa.Index('ix_documents_tender_id', 'tender_id')
    )

    # ### Создание таблицы lots ###
    op.create_table(
        'lots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tender_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('initial_sum', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('delivery_place', sa.String(), nullable=True),
        sa.Column('delivery_term', sa.String(), nullable=True),
        sa.Column('payment_term', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.external_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_lots_id', 'id'),
        sa.Index('ix_lots_tender_id', 'tender_id')
    )

    # ### Создание таблицы filters ###
    op.create_table(
        'filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('calculation', sa.String(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('provider_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('condition', sa.Text(), nullable=True),
        sa.Column('success_action', sa.Integer(), nullable=True),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('formula_target', sa.Text(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['filters.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_filters_id', 'id')
    )

    # ### Создание таблицы errors ###
    op.create_table(
        'errors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tender_id', sa.String(), nullable=False),
        sa.Column('module', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.external_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_errors_id', 'id'),
        sa.Index('ix_errors_tender_id', 'tender_id')
    )

    # ### Создание таблицы ai_checks ###
    op.create_table(
        'ai_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tender_id', sa.String(), nullable=False),
        sa.Column('ai_status', sa.String(), nullable=False),
        sa.Column('ai_response', sa.Text(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.external_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_ai_checks_id', 'id'),
        sa.Index('ix_ai_checks_tender_id', 'tender_id'),
        sa.Column('task_id', sa.Text(), nullable=True)
    )

def downgrade():
    op.drop_index('ix_ai_checks_tender_id', table_name='ai_checks')
    op.drop_table('ai_checks')
    op.drop_index('ix_errors_tender_id', table_name='errors')
    op.drop_table('errors')
    op.drop_table('filters')
    op.drop_index('ix_lots_tender_id', table_name='lots')
    op.drop_table('lots')
    op.drop_index('ix_documents_tender_id', table_name='documents')
    op.drop_table('documents')
    op.drop_table('tenders')