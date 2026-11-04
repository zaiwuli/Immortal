CREATE INDEX IF NOT EXISTS ix_subscribe_status
    ON subscribe(status);

CREATE INDEX IF NOT EXISTS ix_subscribe_create_time
    ON subscribe(create_time);

CREATE INDEX IF NOT EXISTS ix_subscribe_update_time
    ON subscribe(update_time);

CREATE INDEX IF NOT EXISTS ix_cast_subscribe_status
    ON cast_subscribe(status);

CREATE INDEX IF NOT EXISTS ix_general_subscribe_status
    ON general_subscribe(status);

CREATE INDEX IF NOT EXISTS ix_task_enable
    ON task(enable);

CREATE INDEX IF NOT EXISTS ix_task_log_success
    ON task_log(success);

CREATE INDEX IF NOT EXISTS ix_task_log_create_time
    ON task_log(create_time);

CREATE INDEX IF NOT EXISTS ix_download_log_downloader
    ON download_log(downloader);

CREATE INDEX IF NOT EXISTS ix_download_log_create_time
    ON download_log(create_time);

CREATE INDEX IF NOT EXISTS ix_movie_release_date
    ON movie(release_date);

CREATE INDEX IF NOT EXISTS ix_article_publish_date
    ON article(publish_date);

CREATE INDEX IF NOT EXISTS ix_article_website
    ON article(website);

CREATE INDEX IF NOT EXISTS ix_article_section
    ON article(section);

CREATE INDEX IF NOT EXISTS ix_article_category
    ON article(category);
