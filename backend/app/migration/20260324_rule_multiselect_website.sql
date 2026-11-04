-- Rule migration: normalize website/section/category to varchar(255)[] and repair wrapped values.

DO $$
DECLARE
    website_udt text;
    section_udt text;
    category_udt text;
BEGIN
    SELECT udt_name INTO website_udt
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'rule' AND column_name = 'website';

    IF website_udt IS NULL THEN
        EXECUTE 'ALTER TABLE "rule" ADD COLUMN website varchar(255)[]';
    ELSIF website_udt <> '_varchar' THEN
        EXECUTE '
            ALTER TABLE "rule"
            ALTER COLUMN website TYPE varchar(255)[]
            USING CASE
                     WHEN website IS NULL OR btrim(website::text) = '''' THEN ARRAY[''ALL'']::varchar(255)[]
                     ELSE ARRAY[website::text]::varchar(255)[]
                 END
        ';
    ELSE
        EXECUTE 'ALTER TABLE "rule" ALTER COLUMN website TYPE varchar(255)[]';
    END IF;

    SELECT udt_name INTO section_udt
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'rule' AND column_name = 'section';

    IF section_udt <> '_varchar' THEN
        EXECUTE '
            ALTER TABLE "rule"
            ALTER COLUMN section TYPE varchar(255)[]
            USING CASE
                     WHEN section IS NULL OR btrim(section::text) = '''' THEN ARRAY[''ALL'']::varchar(255)[]
                     ELSE ARRAY[section::text]::varchar(255)[]
                 END
        ';
    ELSE
        EXECUTE 'ALTER TABLE "rule" ALTER COLUMN section TYPE varchar(255)[]';
    END IF;

    SELECT udt_name INTO category_udt
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'rule' AND column_name = 'category';

    IF category_udt <> '_varchar' THEN
        EXECUTE '
            ALTER TABLE "rule"
            ALTER COLUMN category TYPE varchar(255)[]
            USING CASE
                     WHEN category IS NULL OR btrim(category::text) = '''' THEN ARRAY[''ALL'']::varchar(255)[]
                     ELSE ARRAY[category::text]::varchar(255)[]
                 END
        ';
    ELSE
        EXECUTE 'ALTER TABLE "rule" ALTER COLUMN category TYPE varchar(255)[]';
    END IF;
END $$;

UPDATE "rule"
SET website = CASE
                  WHEN website IS NULL OR coalesce(array_length(website, 1), 0) = 0 THEN ARRAY['ALL']::varchar(255)[]
                  ELSE ARRAY(
                      SELECT COALESCE(NULLIF(btrim(trim(both '{}' FROM item)), ''), 'ALL')
                      FROM unnest(website) AS item
                  )::varchar(255)[]
              END,
    section = CASE
                  WHEN section IS NULL OR coalesce(array_length(section, 1), 0) = 0 THEN ARRAY['ALL']::varchar(255)[]
                  ELSE ARRAY(
                      SELECT COALESCE(NULLIF(btrim(trim(both '{}' FROM item)), ''), 'ALL')
                      FROM unnest(section) AS item
                  )::varchar(255)[]
              END,
    category = CASE
                   WHEN category IS NULL OR coalesce(array_length(category, 1), 0) = 0 THEN ARRAY['ALL']::varchar(255)[]
                   ELSE ARRAY(
                       SELECT COALESCE(NULLIF(btrim(trim(both '{}' FROM item)), ''), 'ALL')
                       FROM unnest(category) AS item
                   )::varchar(255)[]
               END;
