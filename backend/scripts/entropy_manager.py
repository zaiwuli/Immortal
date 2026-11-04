#!/usr/bin/env python3
"""
熵管理脚本

检测和报告项目中的熵（无用代码、孤立资源等）：
1. 检测孤立路由 — 在 v1 下但未注册到 ROUTER_SPECS
2. 检测孤立下载器 — 在 downloadclient 下但未注册
3. 检测孤立推送器 — 在 notification 下但未注册
4. 检测过期配置 — 数据库中有但代码中已不存在的配置键
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"


class EntropyReporter:
    def __init__(self):
        self.orphan_routes: list[str] = []
        self.orphan_downloadclients: list[str] = []
        self.orphan_notifiers: list[str] = []
        self.stale_configs: list[str] = []

    def has_issues(self) -> bool:
        return bool(
            self.orphan_routes
            or self.orphan_downloadclients
            or self.orphan_notifiers
            or self.stale_configs
        )

    def report(self) -> str:
        lines = []
        if self.orphan_routes:
            lines.append(f"\n[Orphan Routes] {len(self.orphan_routes)} 个")
            for item in self.orphan_routes:
                lines.append(f"  - {item}")

        if self.orphan_downloadclients:
            lines.append(f"\n[Orphan DownloadClients] {len(self.orphan_downloadclients)} 个")
            for item in self.orphan_downloadclients:
                lines.append(f"  - {item}")

        if self.orphan_notifiers:
            lines.append(f"\n[Orphan Notifiers] {len(self.orphan_notifiers)} 个")
            for item in self.orphan_notifiers:
                lines.append(f"  - {item}")

        if self.stale_configs:
            lines.append(f"\n[Stale Configs] {len(self.stale_configs)} 个")
            for item in self.stale_configs:
                lines.append(f"  - {item}")

        return "\n".join(lines) if lines else ""


def detect_orphan_routes() -> list[str]:
    """检测未注册的路由"""
    init_file = APP_DIR / "api" / "__init__.py"
    if not init_file.exists():
        return ["app/api/__init__.py 不存在"]

    content = init_file.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]

    registered = set()
    for match in re.finditer(r"\('app\.api\.v1\.(\w+)'", content):
        registered.add(match.group(1))

    api_v1_dir = APP_DIR / "api" / "v1"
    orphans = []

    if api_v1_dir.exists():
        for py_file in api_v1_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            if py_file.stem not in registered:
                orphans.append(f"app.api.v1.{py_file.stem}")

    return orphans


def detect_orphan_downloadclients() -> list[str]:
    """检测未注册的下载器客户端"""
    init_file = APP_DIR / "api" / "__init__.py"
    if not init_file.exists():
        return ["app/api/__init__.py 不存在"]

    content = init_file.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]

    # 提取已注册的下载器模块
    registered = set()
    for match in re.finditer(r"\(\s*'([^']+\.downloadclient\.[^']+)'\s*,", content):
        module_path = match.group(1)
        parts = module_path.split(".")
        if len(parts) >= 1:
            registered.add(parts[-1])

    downloadclient_dir = APP_DIR / "modules" / "downloadclient"
    orphans = []

    if downloadclient_dir.exists():
        for py_file in downloadclient_dir.rglob("*.py"):
            name = py_file.name
            if name.startswith("_"):
                continue
            stem = py_file.stem
            if stem in ("base", "manager"):
                continue
            if stem.endswith("_pb2") or stem.endswith("_pb2_grpc"):
                continue
            if stem not in registered:
                orphans.append(f"app.modules.downloadclient.{stem}")

    return orphans


def detect_orphan_notifiers() -> list[str]:
    """检测未注册的推送器"""
    init_file = APP_DIR / "api" / "__init__.py"
    if not init_file.exists():
        return ["app/api/__init__.py 不存在"]

    content = init_file.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]

    # 提取已注册的推送器模块
    registered = set()
    for match in re.finditer(r"\(\s*'([^']+\.notification\.[^']+)'\s*,", content):
        module_path = match.group(1)
        parts = module_path.split(".")
        if len(parts) >= 1:
            registered.add(parts[-1])

    notification_dir = APP_DIR / "modules" / "notification"
    orphans = []

    if notification_dir.exists():
        for py_file in notification_dir.rglob("*.py"):
            name = py_file.name
            if name.startswith("_"):
                continue
            stem = py_file.stem
            if stem in ("base", "manager"):
                continue
            if stem.startswith("WXBizMsgCrypt"):
                continue
            if stem not in registered:
                orphans.append(f"app.modules.notification.{stem}")

    return orphans


def detect_stale_configs() -> list[str]:
    """检测过期的配置键"""
    # 从 enums 中提取所有配置键
    config_keys = set()

    enum_file = APP_DIR / "enums" / "__init__.py"
    if enum_file.exists():
        content = enum_file.read_text(encoding="utf-8")
        if content.startswith("\ufeff"):
            content = content[1:]

        for match in re.finditer(r'\.value\s*=\s*"([^"]+)"', content):
            config_keys.add(match.group(1))

    # 这个检测需要数据库访问，暂时只报告代码中已知的配置键
    return []


def main():
    print("=" * 50)
    print("熵管理分析")
    print("=" * 50)

    reporter = EntropyReporter()

    # 1. 检测 orphan routes
    print("\n[1/4] 检测未注册的路由...")
    reporter.orphan_routes = detect_orphan_routes()
    if reporter.orphan_routes:
        print(f"  发现 {len(reporter.orphan_routes)} 个未注册的路由")
    else:
        print("  无")

    # 2. 检测 orphan downloadclients
    print("\n[2/4] 检测未注册的下载器...")
    reporter.orphan_downloadclients = detect_orphan_downloadclients()
    if reporter.orphan_downloadclients:
        print(f"  发现 {len(reporter.orphan_downloadclients)} 个未注册的下载器")
    else:
        print("  无")

    # 3. 检测 orphan notifiers
    print("\n[3/4] 检测未注册的推送器...")
    reporter.orphan_notifiers = detect_orphan_notifiers()
    if reporter.orphan_notifiers:
        print(f"  发现 {len(reporter.orphan_notifiers)} 个未注册的推送器")
    else:
        print("  无")

    # 4. 检测 stale configs
    print("\n[4/4] 检测过期配置...")
    reporter.stale_configs = detect_stale_configs()
    print("  需要数据库访问才能检测 (跳过)")

    # 输出报告
    report = reporter.report()
    if report:
        print("\n" + "=" * 50)
        print("熵检测报告")
        print("=" * 50)
        print(report)
        print("\n建议: 清理上述孤立代码或注册缺失的模块")
        sys.exit(1)
    else:
        print("\n" + "=" * 50)
        print("未检测到熵增问题")
        print("=" * 50)
        sys.exit(0)


if __name__ == "__main__":
    main()
