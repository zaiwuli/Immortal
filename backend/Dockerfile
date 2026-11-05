FROM node:22-slim AS frontend
WORKDIR /source/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --ignore-scripts
COPY frontend/ ./
RUN node node_modules/typescript/bin/tsc -b && node node_modules/vite/bin/vite.js build

FROM python:3.11-slim
WORKDIR /app
ENV DOCKER_ENV=true PYTHONUNBUFFERED=1 TZ=Asia/Shanghai SEHUATANG_COLLECTOR_VERSION=0.1.0
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from sqlalchemy import create_engine; [create_engine('postgresql+' + driver + '://postgres:postgres@localhost/avdb').dispose() for driver in ('psycopg', 'psycopg2')]"
COPY backend/app ./app
COPY --from=frontend /source/backend/frontend/dist /frontend/dist
CMD ["python", "-m", "app.server"]
