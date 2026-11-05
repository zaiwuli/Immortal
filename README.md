# 色花堂采集器

仓库：https://github.com/zaiwuli/sehuatang-collector

无账号的色花堂采集后台，支持文章管理、CSV 导入、智能增量或指定页采集、转换同步和中文日志。仅部署于可信网络。

## Docker 部署

镜像：`ghcr.io/zaiwuli/sehuatang-collector:latest`，GitHub Actions 构建 linux/amd64 与 linux/arm64。

复制 `.env.example` 为 `.env`，将 DATABASE_URL 指向已经初始化的 Avdb PostgreSQL 数据库，然后执行：

```sh
docker compose pull
docker compose up -d
```

打开 `http://主机:8000`。首次拉取 GHCR 镜像如果需要认证，请在 GitHub Packages 将包设为公开，或使用有 read:packages 权限的凭据登录 ghcr.io。

## 数据库

启动先检查 Avdb 原有 `article` 表及所需字段；缺少时启动失败，不自行创建或迁移 Avdb 主表。只自动创建以下 6 张采集器表：

- immortal_article：采集与 CSV 导入的原始记录
- immortal_article_converted：转换结果、内容指纹及同步状态
- immortal_task：采集计划
- immortal_batch：批次汇总
- immortal_task_log：采集日志
- immortal_config：网络及同步设置

不会创建额外的测试目标表或批次明细表。已有 immortal_ 表直接复用，不自动改名、迁移或删除 sehuatang_collector_ 表，以免操作其他工具的数据。如上一版本已经在该前缀下存有采集数据，需要确认归属后再单独迁移。不要将开发测试库直接当作正式 Avdb 使用。

## 采集和同步

不填结束页时按原源码的同站点同板块历史最大 TID 提前停止，最多 100 页；填写结束页则按范围抓取。两种方式均按 website + tid 跳过已有帖子。CSV 导入记录同样参与历史判断。

实时同步由爬取新增入库触发，无新增不触发；定时同步按 Cron 执行。独立兜底补同步定期处理遗漏及失败记录。所有触发共用同步锁，成功且内容未变化的记录跳过。CSV 导入可手动处理，定时或兜底也会处理。

magnet 与 edk 数组去重后换行写入 Avdb magnet，图片以逗号连接；已有同 tid 同站点仅标记存在，不覆盖。不同站点 ID 冲突保留待处理。

文章管理支持多选板块清理原始和关联转换记录，不删除 Avdb 主表。删除历史记录会改变智能爬取的停止依据。

## 本地构建

前端 `cd frontend && pnpm install && pnpm build`。后端安装 backend/requirements.txt，通过环境变量提供 DATABASE_URL，运行 `cd backend && python -m uvicorn app.api:app --host 127.0.0.1 --port 8000`。

镜像构建：`docker build -f backend/Dockerfile -t collector .`。推送 main、v 开头标签或手动运行 Actions 均会构建镜像。测试、运行数据、CSV 原始文件和本地密钥配置不提交。

## 失败与冲突处理

文章管理可按同步状态筛选，勾选记录或选择筛选全部后批量处理。
大小超出目标范围的失败项可预览确认“大小留空并同步”；仅转换结果和目标 size 写为 NULL，原始大小保留。正常 size 继续按 MB 原值传递。
冲突项由用户确认使用备用 TID（原始 TID × 10001），预览双方信息及占用情况；已占用的不会覆盖。自动同步不主动改号。
转换表增加 target_tid 和 size_cleared 字段，启动自动补充，无新增表。成功映射持久保存，后续同步复用。

实时同步遇到其他同步占用时在后台等待，不丢弃新增批次。正常采集结束后等待队列并补处理本批次待同步文章，页面显示采集与同步阶段；失败和冲突仍需手动确认。定时模式不触发实时收尾。运行日志最新记录显示在最上方。
