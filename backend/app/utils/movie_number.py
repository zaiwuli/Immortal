import re

FC2_PATTERN = re.compile(r"(?<![A-Za-z0-9])(FC2)(?:[-_\s]*(PPV))?[-_\s]*(\d{3,8})(?![A-Za-z0-9])", re.IGNORECASE)
GENERAL_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:\d{2,6})?([A-Za-z]{1,10})[-_\s]?(\d{2,6})(?:[A-Za-z]{1,5})?(?![A-Za-z0-9])", re.IGNORECASE)
SEPARATOR_PATTERN = re.compile(r"[\u3000\u3001\u3002\uff0c\uff1b,;\n\r\t\s]+")


def normalize_movie_number_text(text: str) -> str:
    if not text:
        return ''

    normalized = FC2_PATTERN.sub(lambda match: f"FC2-{match.group(3)}", text)

    def replace_general(match: re.Match[str]) -> str:
        prefix = match.group(1)
        suffix = match.group(2)
        if prefix.lower() == 'ppv':
            return match.group(0)
        return f"{prefix.upper()}-{suffix}"

    return GENERAL_PATTERN.sub(replace_general, normalized)


def extract_movie_numbers(text: str) -> list[str]:
    normalized = normalize_movie_number_text(text)
    if not normalized:
        return []

    numbers: list[str] = []
    seen: set[str] = set()

    for _, _, digits in FC2_PATTERN.findall(normalized):
        value = f"FC2-{digits}"
        if value not in seen:
            seen.add(value)
            numbers.append(value)

    for prefix, suffix in GENERAL_PATTERN.findall(normalized):
        if prefix.lower() == 'ppv':
            continue
        value = f"{prefix.upper()}-{suffix}"
        if value not in seen:
            seen.add(value)
            numbers.append(value)

    return numbers


def extract_primary_movie_number(*texts: str | None) -> str | None:
    for text in texts:
        numbers = extract_movie_numbers(text or '')
        if numbers:
            return numbers[0]
    return None


def looks_like_movie_number_list(text: str) -> bool:
    numbers = extract_movie_numbers(text)
    if not numbers:
        return False

    cleaned = normalize_movie_number_text(text)
    for number in numbers:
        cleaned = cleaned.replace(number, ' ')
        cleaned = cleaned.replace(number.replace('-', ''), ' ')
        cleaned = cleaned.replace(number.replace('-', ' '), ' ')
    cleaned = SEPARATOR_PATTERN.sub('', cleaned)
    return len(numbers) >= 2 or len(cleaned) <= 12
