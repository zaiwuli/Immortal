"""Container entry point with unified console logging."""
from app.utils.log import logger
import uvicorn

if __name__ == '__main__':
    logger.info('色花堂采集器正在启动')
    uvicorn.run('app.api:app', host='0.0.0.0', port=8000,
                log_config=None, access_log=False)
