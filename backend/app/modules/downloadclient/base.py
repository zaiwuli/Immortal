import time
from abc import ABC, abstractmethod
from typing import Callable, Iterable, TypeVar

T = TypeVar('T')


class BaseDownloader(ABC):
    config: dict
    name: str
    DEFAULT_POLL_TIMEOUT = 60
    DEFAULT_POLL_INTERVAL = 1
    SMALL_FILE_SIZE_THRESHOLD_BYTES = 200 * 1024 * 1024

    @staticmethod
    def wait_until(
        fetcher: Callable[[], T],
        predicate: Callable[[T], bool],
        timeout: int = DEFAULT_POLL_TIMEOUT,
        interval: float = DEFAULT_POLL_INTERVAL,
    ):
        start = time.time()
        last_result = None
        while time.time() - start < timeout:
            last_result = fetcher()
            if predicate(last_result):
                return last_result
            time.sleep(interval)
        return last_result

    @classmethod
    def collect_small_file_ids(
        cls,
        items: Iterable[T],
        size_getter: Callable[[T], int | float | None],
        id_getter: Callable[[T], int | str | None],
        threshold_bytes: int | None = None,
    ) -> list[int | str]:
        small_file_ids = []
        max_size = threshold_bytes or cls.SMALL_FILE_SIZE_THRESHOLD_BYTES
        for item in items or []:
            item_size = size_getter(item)
            item_id = id_getter(item)
            if item_size is None or item_id is None:
                continue
            if item_size < max_size:
                small_file_ids.append(item_id)
        return small_file_ids

    def build_log_context(self, action: str, **fields) -> str:
        context = {'client': self.name, 'action': action, **fields}
        return ' | '.join(
            f'{key}={value}' for key, value in context.items() if value is not None and value != ''
        )

    @abstractmethod
    def download(self, magnet: str, save_path: str) -> tuple[bool, str | None]:
        pass

    @abstractmethod
    def analyze_size(self, magnet: str):
        pass
