# 简化修仙

影视订阅与下载管理。后端位于 backend/，前端位于 frontend/。

## 启动

复制 `.env.example` 为 `.env`，设置数据库密码与媒体目录，再运行：

```sh
docker compose up -d --build
```

打开 `http://localhost:8000/sign-up` 创建唯一管理员账号。
本地开发：后端安装 `backend/requirements.txt`，配置 POSTGRES_* 或 DATABASE_URL 后在 backend 中运行 `python -m app.main`；前端在 frontend 中运行 `pnpm install`、`pnpm dev`，开发代理指向本机 8000 端口。

## 外部 AI / API

在“令牌管理”创建令牌，选择预设或逐项授权。完整令牌只显示一次，数据库仅存摘要。
请求使用 `X-API-Key` 或 `Authorization: Bearer ...`。接口定义 `/openapi.json`，交互文档 `/docs`；`GET /api/v1/tokens/me` 查询当前权限。

权限格式为 `资源:动作`，动作包括 read、write、execute、delete；`*` 为完全控制。配置按下载器、媒体服务器、通知和系统分别检查。完全控制可操作账号和令牌；子令牌不能获得父令牌未持有的权限。令牌支持有效期、停用、吊销及操作记录。
旧版本明文令牌在升级后停用，需要重新创建。JWT 签名密钥默认持久化到 data/.jwt-secret，也可通过 JWT_SECRET 设置；登录有效期为一天。

## 115tools

设置 → 下载器与其他工具 → 其他工具，填写服务地址和在 115tools 创建的 API 令牌，保存后测试连接。可以在分发规则中选择 115tools 默认云目录。实际云目录由 115tools 配置决定，本项目不会将本地保存路径映射成远端目录。

支持手动链接导入、批次查询和订阅自动投递；API 还支持不超过 2 MiB 的种子上传：

- POST /api/v1/tools/115tools/test
- POST /api/v1/tools/115tools/import：JSON text、idempotency_key
- POST /api/v1/tools/115tools/import/torrent：multipart file、idempotency_key
- GET /api/v1/tools/115tools/batches/{batch_id}

登记排队不代表远端下载或解压完成。手动 API 调用方应在超时后使用同一幂等键及同样内容重试；批次归属于保存连接所使用的远端令牌。订阅投递超时不自动重试，请先核实远端任务。稳定契约参考 https://github.com/zaiwuli/115tools/blob/main/docs/api-guide.md 。

## 清理范围

已移除内置页面 Agent、AI Bot、模型调用、SQL 管理接口和界面、在线版本检查及提示。保留普通通知和业务数据库存储、启动迁移。

## 仓库约定

测试目录只在本地使用，通过 .gitignore 排除。压缩包、解压分析目录、依赖、运行数据和密钥配置同样不提交。
