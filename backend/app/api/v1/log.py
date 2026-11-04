from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import data_path
from app.models import User
from app.schemas.response import success

LOG_FILE_PATH = os.path.join(data_path, 'logs', 'app.log')
MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 100

router = APIRouter()


def _empty_payload(page_size: int, before_line_no: int | None, after_line_no: int | None) -> dict[str, Any]:
    return {
        'items': [],
        'total_lines': 0,
        'page_size': page_size,
        'before_line_no': before_line_no,
        'after_line_no': after_line_no,
        'oldest_line_no': None,
        'latest_line_no': None,
        'has_more_before': False,
        'has_more_after': False,
    }


def _build_payload(
    items: list[dict[str, Any]],
    total_lines: int,
    page_size: int,
    before_line_no: int | None,
    after_line_no: int | None,
    has_more_before: bool,
    has_more_after: bool,
) -> dict[str, Any]:
    return {
        'items': items,
        'total_lines': total_lines,
        'page_size': page_size,
        'before_line_no': before_line_no,
        'after_line_no': after_line_no,
        'oldest_line_no': items[0]['line_no'] if items else None,
        'latest_line_no': items[-1]['line_no'] if items else None,
        'has_more_before': has_more_before,
        'has_more_after': has_more_after,
    }


@router.get('/')
def get_logs(
    page_size: int = DEFAULT_PAGE_SIZE,
    before_line_no: int | None = None,
    after_line_no: int | None = None,
    user: User = Depends(get_current_user),
):
    page_size = max(1, min(int(page_size or DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))

    if before_line_no is not None and after_line_no is not None:
        after_line_no = None

    if not os.path.exists(LOG_FILE_PATH):
        return success(_empty_payload(page_size, before_line_no, after_line_no))

    with open(LOG_FILE_PATH, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    total_lines = len(lines)
    entries = [
        {'line_no': index, 'text': line.rstrip('\n')}
        for index, line in enumerate(lines, start=1)
    ]

    if not entries:
        return success(_empty_payload(page_size, before_line_no, after_line_no))

    if after_line_no is not None:
        newer_items = [item for item in entries if item['line_no'] > after_line_no]
        has_more_after = len(newer_items) > page_size
        items = newer_items[-page_size:] if has_more_after else newer_items
        has_more_before = bool(items and items[0]['line_no'] > 1)
        return success(
            _build_payload(items, total_lines, page_size, before_line_no, after_line_no, has_more_before, has_more_after)
        )

    if before_line_no is not None:
        older_items = [item for item in entries if item['line_no'] < before_line_no]
        has_more_before = len(older_items) > page_size
        items = older_items[-page_size:] if has_more_before else older_items
        has_more_after = bool(items and items[-1]['line_no'] < total_lines)
        return success(
            _build_payload(items, total_lines, page_size, before_line_no, after_line_no, has_more_before, has_more_after)
        )

    has_more_before = total_lines > page_size
    items = entries[-page_size:]
    return success(
        _build_payload(items, total_lines, page_size, before_line_no, after_line_no, has_more_before, False)
    )
