#!/usr/bin/env bash
# 容器入口：初始化 SQLite → 启动 gunicorn（回环） → 启动 Nitro（对外）
set -euo pipefail

# 1) 数据目录：SQLite 及其 -journal 文件都落在 volume 上
mkdir -p "$(dirname "${OSCE_DB_PATH:-/data/osce.db}")"

# 2) 幂等建表 + 种子数据。
#    app.py 只在 `if __name__ == "__main__"` 里调用 init_db()，
#    用 gunicorn 启动时不会执行，所以这里必须显式跑一次。
cd /app/backend
python -c "from database import init_db; init_db()"

# 3) Flask 交给 gunicorn：只监听回环，不对外暴露。
#    gthread + timeout 180 —— ai_service.py 单次 LLM 调用 timeout=90，
#    gunicorn 默认 30s 会把慢请求杀掉。
gunicorn \
  --bind 127.0.0.1:5000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --worker-class gthread \
  --timeout "${GUNICORN_TIMEOUT:-180}" \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  app:app &
BACKEND_PID=$!

# 4) Nitro 是唯一对外入口（端口由 PORT / HOST 控制，默认 3000）
cd /app/frontend
node .output/server/index.mjs &
FRONTEND_PID=$!

# 5) 信号转发：docker stop 时一起优雅退出；任一进程退出则整体退出
trap 'kill -TERM "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' TERM INT
wait -n "$BACKEND_PID" "$FRONTEND_PID"
kill -TERM "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
wait
