import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.utils.wrapper import task_monitor


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'y', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'n', 'off', ''}:
            return False
    return default


def _to_int(value: Any, default: int | None = None) -> int | None:
    if value in (None, ''):
        return default
    return int(value)


def _to_keyword_list(value: Any) -> list[str]:
    if value in (None, ''):
        return []
    if isinstance(value, list):
        items = value
    else:
        normalized = str(value).replace('|', ',').replace(';', ',').replace('\n', ',')
        items = normalized.split(',')
    return [str(item).strip() for item in items if str(item).strip()]


def _to_ext_set(value: Any) -> set[str]:
    result = set()
    for item in _to_keyword_list(value):
        ext = item.lower()
        if not ext.startswith('.'):
            ext = f'.{ext}'
        result.add(ext)
    return result


def _iter_files(target_dir: Path, recursive: bool, max_depth: int | None):
    iterator = target_dir.rglob('*') if recursive else target_dir.glob('*')
    for path in iterator:
        if not path.is_file():
            continue
        if max_depth is not None:
            depth = len(path.relative_to(target_dir).parts) - 1
            if depth > max_depth:
                continue
        yield path


@task_monitor
def cleanup_small_files(
    target_dir,
    max_size_kb,
    recursive=False,
    min_age_hours=None,
    max_age_hours=None,
    include_exts=None,
    exclude_exts=None,
    exclude_dir_keywords=None,
    filename_contains=None,
    limit=500,
    dry_run=True,
    delete_empty_dirs=False,
    min_free_space_mb=None,
    keep_latest_count=0,
    max_depth=None,
):
    target_path = Path(str(target_dir)).expanduser()
    if not target_path.exists() or not target_path.is_dir():
        raise ValueError(f'目标目录不存在或不是目录: {target_path}')

    max_size_bytes = int(float(max_size_kb) * 1024)
    recursive = _to_bool(recursive, default=False)
    dry_run = _to_bool(dry_run, default=True)
    delete_empty_dirs = _to_bool(delete_empty_dirs, default=False)
    min_age_hours = _to_int(min_age_hours)
    max_age_hours = _to_int(max_age_hours)
    limit = max(int(limit or 0), 0)
    keep_latest_count = max(int(keep_latest_count or 0), 0)
    min_free_space_mb = _to_int(min_free_space_mb)
    max_depth = _to_int(max_depth)

    include_ext_set = _to_ext_set(include_exts)
    exclude_ext_set = _to_ext_set(exclude_exts)
    exclude_dir_keywords_list = [item.lower() for item in _to_keyword_list(exclude_dir_keywords)]
    filename_keyword_list = [item.lower() for item in _to_keyword_list(filename_contains)]

    if min_age_hours is not None and min_age_hours < 0:
        raise ValueError('min_age_hours must be greater than or equal to 0')
    if max_age_hours is not None and max_age_hours < 0:
        raise ValueError('max_age_hours must be greater than or equal to 0')
    if min_age_hours is not None and max_age_hours is not None and max_age_hours < min_age_hours:
        raise ValueError('max_age_hours must be greater than or equal to min_age_hours')

    now = datetime.now()
    cutoff_time = now - timedelta(hours=min_age_hours) if min_age_hours is not None else None
    recent_cutoff_time = now - timedelta(hours=max_age_hours) if max_age_hours is not None else None

    disk_usage = shutil.disk_usage(target_path)
    free_space_mb = round(disk_usage.free / 1024 / 1024, 2)
    if min_free_space_mb is not None and free_space_mb >= min_free_space_mb:
        return {
            'target_dir': str(target_path),
            'dry_run': dry_run,
            'max_age_hours': max_age_hours,
            'skipped': True,
            'message': f'当前剩余空间 {free_space_mb}MB，高于阈值 {min_free_space_mb}MB，跳过清理。',
            'free_space_mb': free_space_mb,
            'min_free_space_mb': min_free_space_mb,
            'scanned_count': 0,
            'matched_count': 0,
            'selected_count': 0,
            'deleted_count': 0,
            'freed_bytes': 0,
            'deleted_files': [],
            'empty_dirs_deleted_count': 0,
            'empty_dirs_deleted': [],
            'empty_dirs_deleted_total': 0,
            'skipped_keep_latest_count': 0,
            'errors': [],
        }

    scanned_count = 0
    matched_files: list[dict[str, Any]] = []

    for file_path in _iter_files(target_path, recursive=recursive, max_depth=max_depth):
        scanned_count += 1
        try:
            stat = file_path.stat()
        except OSError:
            continue

        parent_text = str(file_path.parent).lower()
        if exclude_dir_keywords_list and any(keyword in parent_text for keyword in exclude_dir_keywords_list):
            continue

        suffix = file_path.suffix.lower()
        if include_ext_set and suffix not in include_ext_set:
            continue
        if exclude_ext_set and suffix in exclude_ext_set:
            continue

        name_lower = file_path.name.lower()
        if filename_keyword_list and not any(keyword in name_lower for keyword in filename_keyword_list):
            continue

        if stat.st_size > max_size_bytes:
            continue

        modified_at = datetime.fromtimestamp(stat.st_mtime)
        if cutoff_time is not None and modified_at > cutoff_time:
            continue
        if recent_cutoff_time is not None and modified_at < recent_cutoff_time:
            continue

        matched_files.append({
            'path': file_path,
            'size': stat.st_size,
            'modified_at': modified_at,
            'parent': str(file_path.parent),
        })

    matched_count = len(matched_files)
    skipped_keep_latest_count = 0
    if keep_latest_count > 0 and matched_files:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in matched_files:
            grouped[item['parent']].append(item)

        retained: list[dict[str, Any]] = []
        for items in grouped.values():
            items.sort(key=lambda entry: entry['modified_at'], reverse=True)
            skipped_keep_latest_count += min(len(items), keep_latest_count)
            retained.extend(items[keep_latest_count:])
        matched_files = retained

    matched_files.sort(key=lambda entry: (entry['modified_at'], entry['size']))
    selected_files = matched_files[:limit] if limit else matched_files

    deleted_count = 0
    freed_bytes = 0
    deleted_files: list[str] = []
    errors: list[str] = []

    for item in selected_files:
        file_path: Path = item['path']
        deleted_files.append(str(file_path))
        if dry_run:
            freed_bytes += item['size']
            continue
        try:
            file_path.unlink()
            deleted_count += 1
            freed_bytes += item['size']
        except OSError as exc:
            errors.append(f'{file_path}: {exc}')

    empty_dirs_deleted_count = 0
    empty_dirs_deleted: list[str] = []

    if delete_empty_dirs and recursive and not dry_run:
        candidate_dirs = sorted(
            [path for path in target_path.rglob('*') if path.is_dir()],
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for directory in candidate_dirs:
            try:
                if any(directory.iterdir()):
                    continue

                if max_depth is not None:
                    depth = len(directory.relative_to(target_path).parts) - 1
                    if depth > max_depth:
                        continue

                dir_text = str(directory).lower()
                if exclude_dir_keywords_list and any(keyword in dir_text for keyword in exclude_dir_keywords_list):
                    continue

                directory.rmdir()
                empty_dirs_deleted_count += 1
                empty_dirs_deleted.append(str(directory))
            except OSError:
                continue

    deleted_preview = deleted_files[:20]
    empty_dirs_deleted_preview = empty_dirs_deleted[:20]

    message = (
        f'模拟匹配 {len(selected_files)} 个文件。'
        if dry_run
        else f'已删除 {deleted_count} 个文件，释放 {freed_bytes} 字节，并删除 {empty_dirs_deleted_count} 个空目录。'
    )

    return {
        'target_dir': str(target_path),
        'dry_run': dry_run,
        'recursive': recursive,
        'max_size_kb': int(max_size_kb),
        'min_age_hours': min_age_hours,
        'max_age_hours': max_age_hours,
        'free_space_mb': free_space_mb,
        'min_free_space_mb': min_free_space_mb,
        'scanned_count': scanned_count,
        'matched_count': matched_count,
        'selected_count': len(selected_files),
        'deleted_count': deleted_count if not dry_run else 0,
        'freed_bytes': freed_bytes,
        'deleted_files': deleted_preview,
        'deleted_files_total': len(deleted_files),
        'empty_dirs_deleted_count': empty_dirs_deleted_count,
        'empty_dirs_deleted': empty_dirs_deleted_preview,
        'empty_dirs_deleted_total': len(empty_dirs_deleted),
        'skipped_keep_latest_count': skipped_keep_latest_count,
        'errors': errors[:20],
        'message': message,
    }
