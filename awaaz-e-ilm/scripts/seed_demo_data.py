#!/usr/bin/env python3
"""Seed demo data for Awaaz-e-Ilm.

Creates the default user (if not present) and optionally inserts a sample
document record for testing the UI without uploading a real file.

Usage:
    # From repo root:
    python scripts/seed_demo_data.py

    # With a sample document:
    python scripts/seed_demo_data.py --sample-doc

Environment:
    DATABASE_URL — defaults to sqlite+aiosqlite:///./backend/awaaz.db
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Allow importing app package
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


async def seed(add_sample_doc: bool = False) -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.db.models import Base, Chapter, ChapterStatus, Document, DocumentStatus, User

    db_url = os.environ.get(
        "DATABASE_URL", "sqlite+aiosqlite:///./backend/awaaz.db"
    )
    print(f"🗄  Using database: {db_url}")

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # ── Default user ──────────────────────────────────────────────────
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            user = User(name="Default User", preferred_lang="en", speech_rate=1.0)
            session.add(user)
            await session.flush()
            print(f"   ✅ Created user: {user.name} (id={user.id})")
        else:
            print(f"   ℹ  User already exists: {user.name} (id={user.id})")

        # ── Sample document ───────────────────────────────────────────────
        if add_sample_doc:
            doc = Document(
                user_id=user.id,
                title="Introduction to Computer Science (Demo)",
                filename="sample.txt",
                file_type="txt",
                source_lang="en",
                status=DocumentStatus.ready,
            )
            session.add(doc)
            await session.flush()
            print(f"   ✅ Created document: '{doc.title}' (id={doc.id})")

            # Sample chapters
            for i, title in enumerate([
                "Chapter 1: What is a Computer?",
                "Chapter 2: History of Computing",
                "Chapter 3: Algorithms and Data Structures",
            ]):
                ch = Chapter(
                    document_id=doc.id,
                    index=i,
                    title=title,
                    lang="en",
                    status=ChapterStatus.ready,
                )
                session.add(ch)
            print(f"   ✅ Created 3 sample chapters")

        await session.commit()

    await engine.dispose()
    print("\n✅ Seed complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Awaaz-e-Ilm demo data")
    parser.add_argument(
        "--sample-doc",
        action="store_true",
        help="Create a sample document with chapters",
    )
    args = parser.parse_args()
    asyncio.run(seed(add_sample_doc=args.sample_doc))


if __name__ == "__main__":
    main()
