import re
from asyncio import timeout

from app.core.config import config_manager
from app.utils import safe_post
from app.utils.log import logger
from pyquery import PyQuery as pq


class Library:
    domain = 'https://www.javlibrary.com'
    BESTRATED = 'vl_bestrated'
    MOSTWANTED = 'vl_mostwanted'
    STAR_MOSTFAV = 'star_mostfav'

    def crawler_html(self, url, session):
        flare_solver_url = config_manager.get().FLARE_SOLVERR_URL
        if not flare_solver_url:
            logger.warning("未配置 FlareSolverr，无法抓取 JavLibrary 页面")
            return None
        flare_url = flare_solver_url.rstrip('/')
        flare_url = flare_url if flare_url.endswith("/v1") else f"{flare_url}/v1"
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
            "session": session,
            "tabs_till_verify": 8
        }
        res = safe_post(flare_url,
                        headers={"Content-Type": "application/json"},
                        timeout=70,
                        json=payload)
        if not res:
            return None
        try:
            result = res.json()
        except Exception:
            return None
        solution = result.get("solution", {})
        status = solution.get("status")
        if status == 200:
            return solution.get("response")
        return None

    def get_top_movie(self, rank_type, page, session):
        top_url = f"{self.domain}/cn/{rank_type}.php?page={page}"
        html = self.crawler_html(top_url, session)
        movies = []
        if html:
            doc = pq(html)
            for item in doc(".video").items():
                raw_number = item.find(".id").text().strip()
                raw_number = re.sub(r'^\d+([A-Za-z])', r'\1', raw_number) if raw_number else raw_number
                movies.append({
                    "number": raw_number,
                    "title": item.find(".title").text().strip(),
                    "banner": item.find("img").attr("src").replace("ps.jpg", "pl.jpg"),
                    "poster": item.find("img").attr("src")
                })

        return movies

    def get_top_actor(self, session):
        top_url = f"{self.domain}/cn/{self.STAR_MOSTFAV}.php"
        html = self.crawler_html(top_url, session)
        if not html:
            return []
        doc = pq(html)
        stars = []

        for item in doc(".starbox .searchitem").items():
            img = item.find("img")

            name = img.attr("title")
            avatar = img.attr("src")

            if avatar and avatar.startswith("//"):
                avatar = "https:" + avatar

            stars.append({
                "name": name,
                "avatar": avatar
            })
        return stars


library = Library()
