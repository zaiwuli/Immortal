from abc import ABC, abstractmethod


class BaseMediaServer(ABC):
    """
    媒体服务器基础类
    """

    config: dict
    name: str

    def __init__(self, conf: dict):
        self.config = conf or {}

    @abstractmethod
    def has_movie_by_number(self, number: str) -> bool:
        """
        根据番号查询影片是否存在

        :param number: 影片番号
        :return: 存在返回 True，否则 False
        """
        raise NotImplementedError
