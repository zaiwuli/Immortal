import hashlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import requests
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.core.config import config_manager
from app.utils.log import logger

router = APIRouter()

# 简单的内存缓存（生产环境建议用 Redis）
IMAGE_CACHE = {}
CACHE_TTL = 86400 * 7  # 24小时


@lru_cache(maxsize=1000)
def generate_etag(url: str) -> str:
    """生成 ETag"""
    return f'"{hashlib.md5(url.encode()).hexdigest()}"'


def get_cached_image(url: str):
    """从缓存获取图片"""
    if url in IMAGE_CACHE:
        cache_data = IMAGE_CACHE[url]
        # 检查是否过期
        if datetime.now(timezone.utc).timestamp() - cache_data['timestamp'] < CACHE_TTL:
            return cache_data
    return None


def set_cached_image(url: str, content: bytes, content_type: str):
    """缓存图片"""
    IMAGE_CACHE[url] = {
        'content': content,
        'content_type': content_type,
        'timestamp': datetime.now(timezone.utc).timestamp()
    }

    # 简单的缓存清理：超过1000个就清空
    if len(IMAGE_CACHE) > 1000:
        IMAGE_CACHE.clear()


@router.get("/")
def image_proxy(url: str, request: Request):
    etag = generate_etag(url)

    # 1. 检查客户端缓存（304）
    if_none_match = request.headers.get('if-none-match')
    if if_none_match == etag:
        return Response(
            status_code=304,
            headers={'ETag': etag}
        )

    # 2. 检查服务端内存缓存
    cached = get_cached_image(url)
    if cached:
        return Response(
            content=cached['content'],
            media_type=cached['content_type'],
            headers={
                'Cache-Control': 'public, max-age=31536000, immutable',
                'ETag': etag,
                'X-Cache': 'HIT',
                'Access-Control-Allow-Origin': '*',
            }
        )

    # 3. 从源站获取
    proxies = {
        "http": config_manager.get().PROXY,
        "https": config_manager.get().PROXY
    }
    headers = {
        'Referer': 'https://agaghhh.cc/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, proxies=proxies, headers=headers, timeout=10)

        if response.ok:
            content_type = response.headers.get('content-type', 'image/jpeg')
            content = response.content

            # 存入缓存
            set_cached_image(url, content, content_type)

            expires = datetime.now(timezone.utc) + timedelta(days=365)

            return Response(
                content=content,
                media_type=content_type,
                headers={
                    'Cache-Control': 'public, max-age=31536000, immutable',
                    'ETag': etag,
                    'Last-Modified': datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),
                    'Expires': expires.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                    'X-Cache': 'MISS',
                    'Access-Control-Allow-Origin': '*',
                }
            )
        else:
            logger.error(f"下载图片失败：{response.status_code}")
            return Response(content="Image fetch failed", status_code=response.status_code)

    except Exception as e:
        logger.error(f"下载图片失败：{e}")
        return Response(content=f"Error: {str(e)}", status_code=500)
