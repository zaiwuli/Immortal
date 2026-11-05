"""Initialize collector tables without changing Avdb's article schema."""
from sqlalchemy import inspect, text

LEGACY_TABLES = {
    'immortal_article': 'sehuatang_collector_article',
    'immortal_article_converted': 'sehuatang_collector_article_converted',
    'immortal_task': 'sehuatang_collector_task',
    'immortal_batch': 'sehuatang_collector_batch',
    'immortal_task_log': 'sehuatang_collector_task_log',
    'immortal_config': 'sehuatang_collector_config',
}


def initialize_collector_tables(engine, metadata):
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(704936218)"))
        existing = set(inspect(connection).get_table_names())
        conflicts = [(old, new) for old, new in LEGACY_TABLES.items()
                     if old in existing and new in existing]
        if conflicts:
            raise RuntimeError('检测到新旧采集表同时存在，请先合并数据：' +
                               ', '.join(f'{old} / {new}' for old, new in conflicts))
        for old, new in LEGACY_TABLES.items():
            if old in existing:
                connection.execute(text(f'ALTER TABLE "{old}" RENAME TO "{new}"'))
        metadata.create_all(connection, tables=[
            table for table in metadata.sorted_tables if not table.info.get('external')
        ])
