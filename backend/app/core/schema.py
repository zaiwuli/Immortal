"""Initialize owned tables without touching other applications' tables."""
from sqlalchemy import text


def initialize_collector_tables(engine, metadata):
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(704936218)"))
        metadata.create_all(connection, tables=[
            table for table in metadata.sorted_tables if not table.info.get('external')
        ])
        connection.execute(text('ALTER TABLE immortal_article_converted ADD COLUMN IF NOT EXISTS target_tid BIGINT'))
        connection.execute(text('ALTER TABLE immortal_article_converted ADD COLUMN IF NOT EXISTS size_cleared BOOLEAN DEFAULT FALSE'))
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS immortal_converted_target_tid_unique ON immortal_article_converted(target_tid)'))
