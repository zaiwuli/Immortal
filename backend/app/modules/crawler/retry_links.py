"""Additional first-post link extraction, used exclusively by retry jobs."""
import re
from html import unescape


def extract_links(doc):
    post = doc('[id^="postmessage_"]').eq(0).clone()
    post('.sign, .signature, .quote, blockquote, script, style').remove()
    sources = [post.text() or '']
    sources.extend(a.attr('href') or '' for a in post('a[href]').items())
    magnets, ed2k = [], []
    for source in sources:
        source = unescape(source)
        for match in re.finditer(r'magnet:\?xt=urn:btih:(?:[0-9a-f]{40}|[a-z2-7]{32})(?![a-z0-9])(?:&[a-z0-9_.-]+=[^\s<>"\u3000]*)*', source, re.I):
            magnets.append(match.group().rstrip('。，；）】'))
        ed2k.extend(re.findall(r'ed2k://\|file\|[^|\r\n]+\|\d+\|[0-9a-f]{32}\|(?:h=[a-z2-7]+\|)?/', source, re.I))
    return list(dict.fromkeys(magnets)), list(dict.fromkeys(ed2k))
