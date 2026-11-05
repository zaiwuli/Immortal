# 色花堂采集器

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

不会创建 immortal_article_target 或 immortal_batch_item。旧版本已存在的测试表不自动删除。不要将开发测试库直接当作正式 Avdb 使用。

## 采集和同步

不填结束页时按原源码的同站点同板块历史最大 TID 提前停止，最多 100 页；填写结束页则按范围抓取。两种方式均按 website + tid 跳过已有帖子。CSV 导入记录同样参与历史判断。

实时同步由爬取新增入库触发，无新增不触发；定时同步按 Cron 执行。独立兜底补同步定期处理遗漏及失败记录。所有触发共用同步锁，成功且内容未变化的记录跳过。CSV 导入可手动处理，定时或兜底也会处理。

magnet 与 edk 数组去重后换行写入 Avdb magnet，图片以逗号连接；已有同 tid 同站点仅标记存在，不覆盖。不同站点 ID 冲突保留待处理。

文章管理支持多选板块清理原始和关联转换记录，不删除 Avdb 主表。删除历史记录会改变智能爬取的停止依据。

## 本地构建

前端 `cd frontend && pnpm install && pnpm build`。后端安装 backend/requirements.txt，通过环境变量提供 DATABASE_URL，运行 `cd backend && python -m uvicorn app.api:app --host 127.0.0.1 --port 8000`。

镜像构建：`docker build -f backend/Dockerfile -t collector .`。推送 main、v 开头标签或手动运行 Actions 均会构建镜像。测试、运行数据、CSV 原始文件和本地密钥配置不提交。
