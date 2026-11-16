"""Initial schema migration — creates all 7 core tables.

Revision ID: 0001
Revises: (none)
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False, server_default="Default User"),
        sa.Column("preferred_lang", sa.String(10), nullable=False, server_default="en"),
        sa.Column("speech_rate", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── documents ────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("source_lang", sa.String(10), nullable=True),
        sa.Column(
            "status",
            sa.Enum("uploaded", "extracting", "ready", "failed", name="documentstatus"),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── chapters ─────────────────────────────────────────────────────────────
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("text_path", sa.String(1024), nullable=True),
        sa.Column("lang", sa.String(10), nullable=False, server_default="en"),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "ready", "failed", name="chapterstatus"),
            nullable=False,
            server_default="pending",
        ),
    )

    # ── audio_tracks ─────────────────────────────────────────────────────────
    op.create_table(
        "audio_tracks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id"), nullable=False),
        sa.Column("lang", sa.String(10), nullable=False),
        sa.Column("voice", sa.String(128), nullable=True),
        sa.Column("audio_path", sa.String(1024), nullable=False),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("timing_path", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── playback_state ────────────────────────────────────────────────────────
    op.create_table(
        "playback_state",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_s", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("speed", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("audio_lang", sa.String(10), nullable=False, server_default="en"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── jobs ─────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # ── command_log ───────────────────────────────────────────────────────────
    op.create_table(
        "command_log",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(64), nullable=True),
        sa.Column("params", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("command_log")
    op.drop_table("jobs")
    op.drop_table("playback_state")
    op.drop_table("audio_tracks")
    op.drop_table("chapters")
    op.drop_table("documents")
    op.drop_table("users")
