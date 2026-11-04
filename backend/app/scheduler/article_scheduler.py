from app.api.services.article_service import import_excel
from app.core.database import session_scope
from app.utils import safe_get, logger
from app.utils.wrapper import task_monitor_async


class AsyncFileWrapper:
    def __init__(self, content: bytes, filename: str):
        self._content = content
        self.filename = filename

    async def read(self):
        return self._content


@task_monitor_async
async def sync_article(url, token):
    logger.info(f'开始执行远程资源库同步 | url={url}')
    headers = {
        'X-API-KEY': token
    }
    res = safe_get(url, headers=headers, timeout=600)
    if res:
        logger.info('远程文件下载完成，开始导入资源库数据')
        filename = 'temp.csv'
        file_obj = AsyncFileWrapper(res.content, filename)
        with session_scope() as session:
            result = await import_excel(file_obj, session)
            logger.info('远程资源库同步完成')
            return result

    logger.error(f'远程资源库同步失败，下载文件失败 | url={url}')
    return {'message': '下载excel文件失败'}
