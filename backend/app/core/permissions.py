"""Public capability catalog shared by API authorization and the token UI."""
RESOURCES = {
    'content': '内容与榜单', 'subscriptions': '订阅', 'downloads': '下载',
    'tasks': '定时任务', 'rules': '规则与偏好', 'logs': '运行日志',
    'settings.downloaders': '下载器设置', 'settings.media': '媒体服务器设置',
    'settings.notifications': '通知设置', 'settings.system': '系统设置',
    'tools': '其他工具', 'account': '账号管理', 'tokens': '令牌管理',
}
ACTIONS = {'read': '查看', 'write': '创建与修改', 'execute': '执行', 'delete': '删除'}
PERMISSIONS = {f'{resource}:{action}' for resource in RESOURCES for action in ACTIONS}

def config_resource(key):
    if key.startswith('Downloader.') or key == 'downloaders': return 'settings.downloaders'
    if key.startswith('MediaServer.'): return 'settings.media'
    if key.startswith('Notification.'): return 'settings.notifications'
    if key == 'SubscribePreferenceConfig': return 'rules'
    return 'settings.system'

def required_permission(request):
    path = request.url.path.removeprefix('/api/v1/').strip('/')
    parts = path.split('/')
    head = parts[0]
    action = {'GET': 'read', 'POST': 'write', 'PUT': 'write', 'PATCH': 'write', 'DELETE': 'delete'}.get(request.method, 'read')
    if path.endswith('/search') or path.endswith('/recommend/subscribed') or path.endswith('/cleanup/diagnose'): action = 'read'
    if head == 'subscribes' and parts[-1] == 'cancel': action = 'delete'
    if 'network-search' in parts: action = 'execute'
    if head == 'articles' and 'download' in parts: return 'downloads:execute'
    if head == 'tasks' and len(parts)>1 and parts[1]=='run': action = 'execute'
    if head == 'subscribes' and any('download' in part or 'execute' in part for part in parts): action = 'execute'
    if head == 'tools' and any(part in ('test','import','batches') for part in parts):
        action = 'read' if request.method == 'GET' else 'execute'
    resource = {'articles':'content','movies':'content','casts':'content','rank':'content','img-proxy':'content','subscribes':'subscriptions','download-log':'downloads','tasks':'tasks','rules':'rules','filters':'rules','priorities':'rules','logs':'logs','tokens':'tokens','users':'account','tools':'tools'}.get(head)
    if head == 'tasks' and parts[-1] == 'browse-dirs': resource = 'settings.system'
    if head == 'config':
        key = getattr(request.state, 'config_key', None) or (parts[1] if len(parts)>1 else '')
        resource = config_resource(key)
    if resource is None:
        from fastapi import HTTPException
        raise HTTPException(403, '该接口尚未授权给 API 令牌')
    return f'{resource}:{action}'
