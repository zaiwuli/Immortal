# 修仙 · 色花堂采集器（本地测试版）

打开即用，无账号、令牌。只保留色花堂帖子采集、文章管理、CSV/Excel 导入导出、旧库导入、转换合并和导入数据清理。

## 运行

在 backend/data/app.env 配置 DATABASE_URL，运行 `cd backend` 后 `python -m uvicorn app.api:app --host 127.0.0.1 --port 8000`。前端在 frontend 执行 `pnpm install`、`pnpm build`。本地入口 http://127.0.0.1:8000 。无鉴权后台只应开放给可信内网。

当前连接 immortal 测试库。启动只创建 immortal_ 前缀表，不对原 article 执行结构同步或删表：

- immortal_article：原始文章暂存，按 website + tid 去重
- immortal_task：色花堂计划
- immortal_batch、immortal_batch_item：处理批次与逐条结果
- immortal_task_log：采集日志
- immortal_config：网络配置
- immortal_article_target：模拟 Avdb 主表的测试目标

当前不连接或写入正式 avdb。正式切换尚未开放，不能仅修改连接地址就认为已经支持正式主表。

## 采集

沿用原色花堂列表、详情解析与失败补抓。未填写结束页时，取同站点同板块的历史最大 tid，当前页最小 tid 到达它后停止，最多 100 页。填写结束页则按范围扫描，跳过已存在帖子。暂存表是历史判断依据。

每页结果先保存暂存表，正常完成后自动转换并合并本批数据。停止等待当前请求返回；已保存数据保留，不自动合并。仅允许一个采集任务运行。

## 导入和转换

CSV（UTF-8/GB18030）、XLSX、XLS 导入上限 50 MiB，兼容原数组和文本字段。CSV 可从文章管理导出后重新导入；API `/api/export?format=xlsx` 可导出 Excel。

旧库导入从同一测试库原 article 表只读读取，支持板块，API 额外支持 website、min_tid、max_tid。原表不修改。重复项跳过，不覆盖已存数据。

转换将 match_number 映射为 number，将 magnet + edk 去重并换行合并，将图片以逗号连接。校验必填项、字段长度和 size 的 32 位范围；不更改原始暂存数组。当前保持采集器原有大小单位，不额外换算。

合并仅新增；相同 tid 同站点标记 existing，不同站点标记 conflict。已存在目标不会覆盖。正式 Avdb 的 ED2K 展示仍以实际联调结果为准。

## 按板块清理

导入与转换中可指定文件或旧库来源，仅保留某板块，并可限定导入批次。先预览数量再确认，范围变化需重新预览。

只删除暂存记录，不删除新采集数据、旧 article、测试目标和正式 Avdb。历史判断依赖暂存数据，清理后相关板块可能重新抓取。当前版本不提供旧库删表功能。

## 本次迁移

原 article 中实际 47 条已导入新暂存表；测试目标合并 47 条，重复合并 0 新增。旧表保留。旧的订阅、下载、账号等数据表未删除，代码已退出使用。旧网络设置和定时计划需在新 UI 检查配置后保存，未自动启用，避免触发原计划。

源码改造前备份位于 backend/data/pre-collector-source 与 pre-collector-frontend，属于本地忽略目录。测试目录、本地配置、数据与备份均不提交。本轮不提交或推送 Git。


## 最新 UI 与同步调整

后台仅保留文章管理、采集任务、设置。CSV 是唯一导入入口；旧库导入和 Excel 导入接口已移除。文章管理支持多选板块清理，删除原始及关联转换记录，不删除目标表。

新增 immortal_article_converted 保存转换结果、内容指纹及同步状态。设置支持实时（5 秒检查）或定时（Cron），并独立配置 1–1440 分钟兜底补同步；默认实时及 15 分钟兜底。三种触发共用同步锁，已成功且未变化的记录跳过。冲突不自动重试，失败会重试。当前仍仅写测试目标 immortal_article_target。
