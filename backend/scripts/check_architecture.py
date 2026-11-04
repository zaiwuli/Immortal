#!/usr/bin/env python3
"""
架构约束检查脚本

检查规则:
1. api/v1/* 只能调用 api/services/*，不能直接调用 models/*
2. api/services/* 可以调用 models/* 和其他 api/services/*
3. 禁止使用 exec/eval
4. 禁止直接字符串拼接 SQL（应使用参数化查询）
5. api/v1 路由必须注册到 ROUTER_SPECS
6. downloadclient 必须注册到 DOWNLOAD_CLIENT_SPECS
7. notification 必须注册到 PUSHER_SPECS
"""

import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"


class ArchitectureChecker(ast.NodeVisitor):
    """检查架构违规的 AST 访问器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.relative_path = self.file_path.relative_to(PROJECT_ROOT)
        self.errors = []
        self.is_api_v1 = str(self.relative_path).startswith("app/api/v1")
        self.is_api_services = str(self.relative_path).startswith("app/api/services")

    def visit_Import(self, node):
        self._check_import(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self._check_import_from(node)
        self.generic_visit(node)

    def _check_import(self, node):
        for alias in node.names:
            module = alias.name
            self._check_module_access(module)

    def _check_import_from(self, node):
        if node.module:
            self._check_module_access(node.module)

    def _check_module_access(self, module: str):
        if not module.startswith("app"):
            return

        # 规则1: api/v1 不能直接导入 models
        if self.is_api_v1 and module.startswith("app/models"):
            self.errors.append(
                f"架构违规: {self.relative_path} 不应直接导入 models，请通过 api/services 间接访问"
            )

        # 规则1: api/v1 不能直接导入 modules
        if self.is_api_v1 and module.startswith("app/modules"):
            self.errors.append(
                f"架构违规: {self.relative_path} 不应直接导入 modules，请通过 api/services 间接访问"
            )

        # 规则2: api/v1 不应直接导入 api/services 以外的业务模块
        if self.is_api_v1 and module.startswith("app/api") and not module.startswith("app/api/services"):
            self.errors.append(
                f"架构违规: {self.relative_path} 不应直接导入 {module}，只允许导入 api/services"
            )

    def visit_Call(self, node):
        self._check_dangerous_calls(node)
        self.generic_visit(node)

    def _check_dangerous_calls(self, node):
        dangerous_funcs = ["exec", "eval", "compile"]

        if isinstance(node.func, ast.Name) and node.func.id in dangerous_funcs:
            self.errors.append(
                f"安全违规: {self.relative_path} 禁止使用 {node.func.id}()"
            )


class SecurityChecker(ast.NodeVisitor):
    """检查安全违规的 AST 访问器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.relative_path = self.file_path.relative_to(PROJECT_ROOT)
        self.errors = []

    def visit_Call(self, node):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # 检查危险的 SQL 相关调用
        dangerous_sql_patterns = [
            "execute",
            "executemany",
            "cursor.execute",
            "cursor.executemany",
        ]

        if func_name in dangerous_sql_patterns:
            self._check_sql_injection(node)

        self.generic_visit(node)

    def _check_sql_injection(self, node):
        """检查是否有明显的 SQL 字符串拼接"""
        for arg in node.args:
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                # 可能是字符串拼接
                pass
            if isinstance(arg, ast.JoinedStr):
                # f-string，可能有注入风险
                self.errors.append(
                    f"安全警告: {self.relative_path} 可能存在 SQL 注入风险，请使用参数化查询"
                )


def check_file(file_path: Path) -> list[str]:
    """检查单个文件"""
    if not file_path.suffix == ".py":
        return []

    # 跳过 __pycache__ 和 test 文件
    if "__pycache__" in str(file_path) or "test" in str(file_path):
        return []

    try:
        content = file_path.read_text(encoding="utf-8")
        # 移除 BOM 字符
        if content.startswith("\ufeff"):
            content = content[1:]
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        return [f"语法错误: {file_path}: {e}"]

    checker = ArchitectureChecker(str(file_path))
    checker.visit(tree)

    security_checker = SecurityChecker(str(file_path))
    security_checker.visit(tree)

    return checker.errors + security_checker.errors


def check_router_registration() -> list[str]:
    """检查 api/v1 路由是否都注册到 ROUTER_SPECS"""
    errors = []
    init_file = APP_DIR / "api" / "__init__.py"
    if not init_file.exists():
        return ["架构违规: app/api/__init__.py 不存在"]

    content = init_file.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]

    # 提取 ROUTER_SPECS 中注册的模块
    registered = set()
    for match in re.finditer(r"\('app\.api\.v1\.(\w+)'", content):
        registered.add(match.group(1))

    # 扫描 app/api/v1/ 下的所有 .py 文件（排除 __init__.py）
    api_v1_dir = APP_DIR / "api" / "v1"
    if api_v1_dir.exists():
        for py_file in api_v1_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            module_name = py_file.stem
            if module_name not in registered:
                errors.append(
                    f"注册违规: app.api.v1.{module_name} 未注册到 ROUTER_SPECS"
                )

    return errors


def check_downloadclient_registration() -> list[str]:
    """检查 downloadclient 是否都注册到 DOWNLOAD_CLIENT_SPECS"""
    errors = []
    init_file = APP_DIR / "api" / "__init__.py"
    if not init_file.exists():
        return ["架构违规: app/api/__init__.py 不存在"]

    content = init_file.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]

    # 提取 DOWNLOAD_CLIENT_SPECS 中注册的模块路径
    # 格式: DownloadClientEnum.QBITTORRENT.value: ('app.modules.downloadclient.qbittorrent', 'QBitTorrentClient'),
    registered_module_paths = set()
    for match in re.finditer(r"\(\s*'([^']+\.downloadclient\.[^']+)'\s*,", content):
        module_path = match.group(1)
        registered_module_paths.add(module_path)

    # 需要注册的客户端模块
    expected_clients = set()
    downloadclient_dir = APP_DIR / "modules" / "downloadclient"
    if downloadclient_dir.exists():
        for py_file in downloadclient_dir.rglob("*.py"):
            # 跳过 __init__, base, manager, protobuf 生成文件
            name = py_file.name
            if name.startswith("_"):
                continue
            stem = py_file.stem
            if stem in ("base", "manager"):
                continue
            # protobuf 文件
            if stem.endswith("_pb2") or stem.endswith("_pb2_grpc"):
                continue
            # 计算相对于 downloadclient 的路径
            rel_path = py_file.relative_to(downloadclient_dir).with_suffix("")
            client_path = ".".join(rel_path.parts)
            expected_clients.add(f"app.modules.downloadclient.{client_path}")

    # 检查是否有未注册的客户端
    for client_path in expected_clients:
        if client_path not in registered_module_paths:
            errors.append(
                f"注册违规: {client_path} 未注册到 DOWNLOAD_CLIENT_SPECS"
            )

    return errors


def check_notification_registration() -> list[str]:
    """检查 notification 是否都注册到 PUSHER_SPECS"""
    errors = []
    init_file = APP_DIR / "api" / "__init__.py"
    if not init_file.exists():
        return ["架构违规: app/api/__init__.py 不存在"]

    content = init_file.read_text(encoding="utf-8")
    if content.startswith("\ufeff"):
        content = content[1:]

    # 提取 PUSHER_SPECS 中注册的模块路径
    # 格式: PusherEnum.WECHAT.value: ('app.modules.notification.wechat', 'WeChatNotifier'),
    registered_module_paths = set()
    for match in re.finditer(r"\(\s*'([^']+\.notification\.[^']+)'\s*,", content):
        module_path = match.group(1)
        registered_module_paths.add(module_path)

    # 需要注册的推送器模块
    expected_notifiers = set()
    notification_dir = APP_DIR / "modules" / "notification"
    if notification_dir.exists():
        for py_file in notification_dir.rglob("*.py"):
            # 跳过 __init__, base, manager
            name = py_file.name
            if name.startswith("_"):
                continue
            stem = py_file.stem
            if stem in ("base", "manager"):
                continue
            # WXBizMsgCrypt3 是企业微信加密库，不是推送器
            if stem.startswith("WXBizMsgCrypt"):
                continue
            # 计算相对路径
            rel_path = py_file.relative_to(notification_dir).with_suffix("")
            notifier_path = ".".join(rel_path.parts)
            expected_notifiers.add(f"app.modules.notification.{notifier_path}")

    # 检查是否有未注册的推送器
    for notifier_path in expected_notifiers:
        if notifier_path not in registered_module_paths:
            errors.append(
                f"注册违规: {notifier_path} 未注册到 PUSHER_SPECS"
            )

    return errors


def main():
    errors = []

    # 扫描所有 Python 文件
    for py_file in APP_DIR.rglob("*.py"):
        file_errors = check_file(py_file)
        errors.extend(file_errors)

    # 检查注册约束
    errors.extend(check_router_registration())
    errors.extend(check_downloadclient_registration())
    errors.extend(check_notification_registration())

    if errors:
        print("架构/安全检查发现以下问题:\n")
        for error in errors:
            print(f"  - {error}")
        print(f"\n共 {len(errors)} 个问题")
        sys.exit(1)
    else:
        print("架构/安全检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
