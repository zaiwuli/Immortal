update filter
set subtitles = case
                    when subtitles is null then null
                    when '中文' = any (subtitles) then array['中文']::varchar[]
                    else null
end;

update priority
set subtitles = array['中文']::varchar[]
where subtitles is distinct from array['中文']::varchar[];
