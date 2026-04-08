"""
cleanup_service.py  —  Background daily purge of soft-deleted papers.

Papers are soft-deleted (deleted_at is set) when a faculty/admin removes one.
This service runs at app startup and every 24 hours to permanently purge any
paper whose deleted_at timestamp is older than TRASH_RETENTION_DAYS (15).

Permanent purge order:
  1. Delete Qdrant vectors (loses semantic searchability)
  2. Delete the physical PDF file from disk
  3. Delete the SQLite record
  4. Log a "Purge" action to activity_logs
"""

import asyncio
import os
from datetime import datetime, timedelta

TRASH_RETENTION_DAYS = 15


async def _run_purge() -> None:
    """Perform a single purge pass — called at startup and then every 24h."""
    from app.core.database import SessionLocal
    from app.models.paper import Paper
    from app.models.activity_log import ActivityLog
    from app.services.vector_db import vector_db

    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=TRASH_RETENTION_DAYS)
        expired = (
            db.query(Paper)
            .filter(Paper.deleted_at.isnot(None), Paper.deleted_at <= cutoff)
            .all()
        )

        if not expired:
            print(f"[CleanupService] No expired trash entries found.")
            return

        print(f"[CleanupService] Purging {len(expired)} expired paper(s)...")

        for paper in expired:
            paper_id = paper.id
            title = paper.title

            # 1. Remove Qdrant vectors
            try:
                vector_db.delete_paper(paper_id)
            except Exception as e:
                print(f"[CleanupService] Qdrant delete error for paper {paper_id}: {e}")

            # 2. Remove physical PDF file
            if paper.file_path and os.path.exists(paper.file_path):
                try:
                    os.remove(paper.file_path)
                except Exception as e:
                    print(f"[CleanupService] File delete error for paper {paper_id}: {e}")

            # 3. Log the purge before deleting the record
            db.add(ActivityLog(
                action="Purge",
                paper_title=title,
                performed_by="System",
                performed_by_role="System",
            ))

            # 4. Delete the DB record
            db.delete(paper)

        db.commit()
        print(f"[CleanupService] Purge complete. {len(expired)} paper(s) permanently removed.")

    except Exception as e:
        print(f"[CleanupService] Error during purge: {e}")
        db.rollback()
    finally:
        db.close()


async def start_cleanup_loop() -> None:
    """
    Long-running asyncio task:
      - Runs an immediate purge pass at startup
      - Then sleeps 24 hours and repeats indefinitely
    """
    print("[CleanupService] Starting cleanup loop...")
    while True:
        await _run_purge()
        await asyncio.sleep(60 * 60 * 24)  # 24 hours
