import copy
import json

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import session_scope
from app.models.task import Task
from app.modules.crawler.javdb import javdb
from app.modules.crawler.library import library
from app.scheduler.article_scheduler import sync_article
from app.scheduler.download_scheduler import download_by_route, analyze_article_size
from app.scheduler.cleanup_scheduler import cleanup_small_files
from app.scheduler.avbase_scheduler import sync_avbase_daily, sync_avbase_recent
from app.scheduler.movie_scheduler import sync_movies
from app.scheduler.rank_scheduler import sync_library_top_movie, sync_javdb_top_movie, sync_library_top_cast, \
    sync_shared_movie_rank
from app.scheduler.sht_sheduler import sync_sht_by_max_page, sht_section_list
from app.scheduler.subscribe_scheduler import execute_subscribe, execute_rank_subscribe, execute_cast_subscribe, \
    execute_general_subscribe
from app.scheduler.x1080x_scheduler import sync_x1080_by_max_page, x1080x_section_list
from app.scheduler.report_scheduler import push_subscription_report
from app.utils import logger

scheduler = AsyncIOScheduler()


def job_error_listener(event):
    if event.exception:
        logger.error(f'任务 {event.job_id} 执行异常: {event.exception}')


scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)

MOVIE_RANK_NAME_OPTIONS = [
    {'label': '图书馆-最想要', 'value': f'library-{library.MOSTWANTED}'},
    {'label': '图书馆-高评分', 'value': f'library-{library.BESTRATED}'},
    {'label': 'JavDB-有码日榜', 'value': f'javdb-0-{javdb.DAILY}'},
    {'label': 'JavDB-有码周榜', 'value': f'javdb-0-{javdb.WEEKLY}'},
    {'label': 'JavDB-有码月榜', 'value': f'javdb-0-{javdb.MONTHLY}'},
    {'label': 'JavDB-无码日榜', 'value': f'javdb-1-{javdb.DAILY}'},
    {'label': 'JavDB-无码周榜', 'value': f'javdb-1-{javdb.WEEKLY}'},
    {'label': 'JavDB-无码月榜', 'value': f'javdb-1-{javdb.MONTHLY}'},
    {'label': 'JavDB-FC2日榜', 'value': f'javdb-3-{javdb.DAILY}'},
    {'label': 'JavDB-FC2周榜', 'value': f'javdb-3-{javdb.WEEKLY}'},
    {'label': 'JavDB-FC2月榜', 'value': f'javdb-3-{javdb.MONTHLY}'},
]

SHARED_RANK_NAME_OPTIONS = [
    *MOVIE_RANK_NAME_OPTIONS,
    {'label': '图书馆-演员榜', 'value': f'library-{library.STAR_MOSTFAV}'},
]

FUNC_MAP = [

    {
        'func_name': 'sync_sht_by_max_page',
        'func_label': '色花堂爬虫任务',
        'func': sync_sht_by_max_page,
        'func_args_rule': [
            {'label': '起始页码(默认1)', 'key': 'start_page', 'require': False, 'type': 'number'},
            {'label': '最大页码(默认100)', 'key': 'max_page', 'require': False, 'type': 'number'},
            {'label': '板块列表', 'key': 'section_id_list', 'require': False, 'type': 'multi-select',
             'options': sht_section_list}
        ]
    },

    {
        'func_name': 'sync_x1080_by_max_page',
        'func_label': 'X1080X爬虫任务',
        'func': sync_x1080_by_max_page,
        'func_args_rule': [
            {'label': '起始页码(默认1)', 'key': 'start_page', 'require': False, 'type': 'number'},
            {'label': '最大页码(默认100)', 'key': 'max_page', 'require': False, 'type': 'number'},
            {'label': '板块列表', 'key': 'section_id_list', 'require': False, 'type': 'multi-select',
             'options': x1080x_section_list}
        ]
    },
    {
        'func_name': 'analyze_article_size',
        'func_label': '完善磁链体积任务',
        'func': analyze_article_size,
        'func_args_rule': [
            {'label': '发布日期偏移量', 'key': 'offset_days', 'require': True, 'type': 'number'}
        ]
    },
    {
        'func_name': 'download_by_route',
        'func_label': '规则入库任务',
        'func': download_by_route,
        'func_args_rule': [
            {'label': '发布日期偏移量', 'key': 'offset_days', 'require': True, 'type': 'number'},
            {'label': '规则ID列表', 'key': 'rule_id_list', 'require': True, 'type': 'multi-select'}
        ]
    },
    {
        'func_name': 'sync_article',
        'func_label': '远程同步资源库任务',
        'func': sync_article,
        'func_args_rule': [
            {'label': '分享URL', 'key': 'url', 'require': True, 'type': 'string'},
            {'label': '令牌', 'key': 'token', 'require': True, 'type': 'string'}
        ]
    },
    {
        'func_name': 'sync_shared_movie_rank',
        'func_label': '远程同步榜单任务',
        'func': sync_shared_movie_rank,
        'func_args_rule': [
            {'label': '分享URL', 'key': 'url', 'require': True, 'type': 'string'},
            {'label': '令牌', 'key': 'token', 'require': True, 'type': 'string'},
            {'label': '本地榜单列表', 'key': 'rank_name_list', 'require': False, 'type': 'multi-select',
             'options': SHARED_RANK_NAME_OPTIONS}
        ]
    },
    {
        'func_name': 'sync_library_top_movie',
        'func_label': '图书馆榜单爬虫任务',
        'func': sync_library_top_movie,
        'func_args_rule': [
            {'label': '最大页码', 'key': 'max_page', 'require': True, 'type': 'number'},
            {'label': '榜单类型', 'key': 'rank_type_list', 'require': False, 'type': 'multi-select',
             'options':
                 [
                     {'label': '最想要', 'value': library.MOSTWANTED},
                     {'label': '高评分', 'value': library.BESTRATED}
                 ]
             }
        ]
    },
    {
        'func_name': 'sync_javdb_top_movie',
        'func_label': 'JavDB榜单爬虫任务',
        'func': sync_javdb_top_movie,
        'func_args_rule': [
            {'label': '榜单类型', 'key': 'rank_type_list', 'require': False, 'type': 'multi-select',
             'options':
                 [
                     {'label': '有码日榜', 'value': f'0-{javdb.DAILY}'},
                     {'label': '有码周榜', 'value': f'0-{javdb.WEEKLY}'},
                     {'label': '有码月榜', 'value': f'0-{javdb.MONTHLY}'},
                     {'label': '无码日榜', 'value': f'1-{javdb.DAILY}'},
                     {'label': '无码周榜', 'value': f'1-{javdb.WEEKLY}'},
                     {'label': '无码月榜', 'value': f'1-{javdb.MONTHLY}'},
                     {'label': 'FC2日榜', 'value': f'3-{javdb.DAILY}'},
                     {'label': 'FC2周榜', 'value': f'3-{javdb.WEEKLY}'},
                     {'label': 'FC2月榜', 'value': f'3-{javdb.MONTHLY}'},
                 ]
             }
        ]
    },
    {
        'func_name': 'sync_library_top_cast',
        'func_label': '图书馆演员排行榜爬虫任务',
        'func': sync_library_top_cast,
        'func_args_rule': []
    },
    {
        'func_name': 'cleanup_small_files',
        'func_label': '清理目录小文件',
        'func': cleanup_small_files,
        'func_args_rule': [
            {'label': '目标目录', 'key': 'target_dir', 'require': True, 'type': 'directory',
             'description': '要扫描和清理的小文件目录'},
            {'label': '最大文件大小(KB)', 'key': 'max_size_kb', 'require': True, 'type': 'number',
             'description': '小于等于该大小的文件会进入候选集'},
            {'label': '递归子目录', 'key': 'recursive', 'require': False, 'type': 'boolean',
             'description': '开启后会继续扫描子目录'},
            {'label': '最小文件年龄(小时)', 'key': 'min_age_hours', 'require': False, 'type': 'number',
             'description': '只处理多少小时前创建或修改的文件'},
            {'label': '最大文件年龄(小时)', 'key': 'max_age_hours', 'require': False, 'type': 'number',
             'description': '仅处理最近 N 小时内的文件，配合 min_age_hours 可以限定时间范围'},
            {'label': '仅包含后缀', 'key': 'include_exts', 'require': False, 'type': 'string',
             'description': '多个后缀用逗号分隔，例如 .tmp,.log'},
            {'label': '排除后缀', 'key': 'exclude_exts', 'require': False, 'type': 'string',
             'description': '多个后缀用逗号分隔'},
            {'label': '排除目录关键字', 'key': 'exclude_dir_keywords', 'require': False, 'type': 'string',
             'description': '目录路径包含这些关键字时跳过，多个关键字用逗号分隔'},
            {'label': '文件名包含', 'key': 'filename_contains', 'require': False, 'type': 'string',
             'description': '只处理文件名中包含这些关键字的文件，多个关键字用逗号分隔'},
            {'label': '单次处理上限', 'key': 'limit', 'require': False, 'type': 'number',
             'description': '每次最多处理多少个候选文件，0 表示不限制'},
            {'label': '仅预演不删除', 'key': 'dry_run', 'require': False, 'type': 'boolean',
             'description': '开启后只统计匹配结果，不会真的删除文件'},
            {'label': '删除空目录', 'key': 'delete_empty_dirs', 'require': False, 'type': 'boolean',
             'description': '删除完文件后尝试清理空目录'},
            {'label': '剩余空间阈值(MB)', 'key': 'min_free_space_mb', 'require': False, 'type': 'number',
             'description': '仅当磁盘剩余空间低于该值时才执行清理'},
            {'label': '每目录保留最新文件数', 'key': 'keep_latest_count', 'require': False, 'type': 'number',
             'description': '每个目录至少保留最近 N 个候选文件'},
            {'label': '最大扫描深度', 'key': 'max_depth', 'require': False, 'type': 'number',
             'description': '0 表示仅当前目录，1 表示包含一层子目录'}
        ]
    },

    {
        'func_name': 'sync_avbase_daily',
        'func_label': 'AvBase 上新同步',
        'func': sync_avbase_daily,
        'func_args_rule': [
            {'label': '往前偏移天数', 'key': 'backward_offset_days', 'require': False, 'type': 'number'},
            {'label': '往后偏移天数', 'key': 'forward_offset_days', 'require': False, 'type': 'number'}
        ]
    },
    {
        'func_name': 'sync_avbase_recent',
        'func_label': 'AvBase 最近上架同步',
        'func': sync_avbase_recent,
        'func_args_rule': []
    },
    {
        'func_name': 'sync_movies',
        'func_label': '完善影片元数据',
        'func': sync_movies,
        'func_args_rule': []
    },
    {
        'func_name': 'execute_rank_subscribe',
        'func_label': '榜单订阅任务',
        'func': execute_rank_subscribe,
        'func_args_rule': [
            {'label': '榜单列表', 'key': 'rank_name_list', 'require': True, 'type': 'multi-select',
             'options': MOVIE_RANK_NAME_OPTIONS},
            {'label': '订阅数量', 'key': 'limit', 'require': False, 'type': 'number'}
        ]
    },
    {
        'func_name': 'execute_cast_subscribe',
        'func_label': '演员订阅任务',
        'func_args': [],
        'func': execute_cast_subscribe,
        'func_args_rule': []
    },
    {
        'func_name': 'execute_general_subscribe',
        'func_label': '综合订阅任务',
        'func_args': [],
        'func': execute_general_subscribe,
        'func_args_rule': []
    },
    {
        'func_name': 'execute_subscribe',
        'func_label': '订阅下载任务',
        'func_args': [],
        'func': execute_subscribe,
        'func_args_rule': []
    },
    {
        'func_name': 'push_subscription_report',
        'func_label': '订阅报表推送',
        'func': push_subscription_report,
        'func_args_rule': [
            {'label': '报表周期', 'key': 'report_period', 'require': True, 'type': 'select',
             'options': [
                 {'label': '日报', 'value': 'daily'},
                 {'label': '周报', 'value': 'weekly'},
                 {'label': '月报', 'value': 'monthly'}
             ]},
            {'label': '兼容聊天ID列表', 'key': 'chat_ids', 'require': False, 'type': 'string'}
        ]
    },


]


def find_func(func_name):
    for func in FUNC_MAP:
        if func['func_name'] == func_name:
            return func
    return None


def list_task():
    with session_scope() as session:
        tasks = session.query(Task).filter(Task.enable == True).all()
    return tasks


def _load_task_kwargs(task: Task) -> dict | None:
    if not task.task_args:
        return {}
    try:
        kwargs = json.loads(task.task_args)
    except json.JSONDecodeError as exc:
        logger.exception(
            f'定时任务装载跳过，参数不是合法 JSON | task_id={task.id}, func_name={task.task_func}, error={exc}')
        return None
    if not isinstance(kwargs, dict):
        logger.error(f'定时任务装载跳过，参数不是 JSON 对象 | task_id={task.id}, func_name={task.task_func}')
        return None
    return kwargs


def push_job():
    tasks = list_task()
    logger.info(f'开始装载定时任务 | count={len(tasks)}')
    for task in tasks:
        try:
            kwargs = _load_task_kwargs(task)
            if kwargs is None:
                continue
            task_args = copy.deepcopy(kwargs)
            kwargs['_task_context'] = {
                'task_id': task.id,
                'task_name': task.task_name,
                'task_func': task.task_func,
                'task_cron': task.task_cron,
                'task_args': task_args,
                'push_enable': bool(task.push_enable),
                'push_title_template': task.push_title_template,
                'push_message_template': task.push_message_template,
            }
            func = find_func(task.task_func)
            if func:
                scheduler.add_job(
                    func['func'],
                    kwargs=kwargs,
                    trigger=CronTrigger.from_crontab(expr=task.task_cron),
                    max_instances=1,
                    coalesce=True,
                    misfire_grace_time=600,
                )
                logger.info(f'定时任务装载成功 | func_name={task.task_func}, cron={task.task_cron}, kwargs={kwargs}')
            else:
                logger.warning(f'定时任务装载跳过，未找到函数映射 | task_id={task.id}, func_name={task.task_func}')
        except Exception:
            logger.exception(f'定时任务装载失败，已跳过当前任务 | task_id={task.id}, func_name={task.task_func}')


def start_scheduler():
    logger.info('开始启动调度器')
    push_job()
    scheduler.start()
    logger.info('调度器启动完成')


def restart_scheduler():
    logger.info('开始重载调度器任务')
    scheduler.remove_all_jobs()
    push_job()
    logger.info('调度器任务重载完成')
