# syntax=docker/dockerfile:1
#
# OSCE 学生端训练平台 —— 单镜像（Flask 后端 + Nuxt 4 前端）
#
#   构建:  docker build -f docker/Dockerfile -t osce:latest .
#   运行:  docker run -d -p 3000:3000 --env-file backend/.env -v osce-data:/data osce:latest
#
# 只有 3000 端口对外；后端 gunicorn 仅监听容器内回环 127.0.0.1:5000，
# 由 Nitro 的 /api/** 反向代理转发（该代理目标构建期已烘焙进 .output）。

# ---------------------------------------------------------------------------
# Stage 1 — 构建 Nuxt 前端
# ---------------------------------------------------------------------------
FROM node:24-bookworm-slim AS frontend-build

ENV PNPM_HOME=/pnpm
ENV PATH=/pnpm:$PATH
# 与开发机一致的 pnpm 主版本（lockfileVersion 9.0）
RUN npm install -g pnpm@11.22.0 && pnpm config set store-dir /pnpm/store

WORKDIR /build

# 依赖层：仅当 package.json / lockfile 变化时失效
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

# ---------------------------------------------------------------------------
# Stage 2 — 运行时（Python + Node）
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm

# Node 运行时（Nuxt/Nitro 需要）。两个 stage 同为 Debian 12，glibc 兼容。
COPY --from=node:24-bookworm-slim /usr/local /usr/local

ENV NODE_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=3000 \
    HOST=0.0.0.0 \
    OSCE_DB_PATH=/data/osce.db

WORKDIR /app

# 后端依赖（含生产 WSGI 服务器 gunicorn）
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt gunicorn==26.2.0

COPY backend/ /app/backend/
COPY --from=frontend-build /build/.output /app/frontend/.output

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && mkdir -p /data

EXPOSE 3000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
