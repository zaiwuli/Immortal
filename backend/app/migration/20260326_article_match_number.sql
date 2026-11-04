ALTER TABLE article
    ADD COLUMN IF NOT EXISTS match_number varchar(64);

CREATE INDEX IF NOT EXISTS ix_article_match_number
    ON article(match_number);
