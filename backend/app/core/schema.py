"""Initialize owned tables without touching other applications' tables."""
from sqlalchemy import text


def initialize_collector_tables(engine, metadata):
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(704936218)"))
        metadata.create_all(connection, tables=[
            table for table in metadata.sorted_tables if not table.info.get('external')
        ])
