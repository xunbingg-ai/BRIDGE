# 在新电脑上部署 OSCE 镜像

> 面向"拿到镜像、想把系统跑起来"的运维/同事。全程只需要 **Docker**，不需要装 Python、Node、pnpm，也不需要源码。
>
> 镜像：`osce:latest`（Linux **amd64**，约 406 MB）
> 对外端口：**3000**（前端 + `/api` 同一个入口）
> 数据：SQLite 存在 Docker 卷 `/data`（**不挂卷 = 重启/重建容器后数据全丢**）

---

## 0. 五分钟速通（TL;DR）

目标机器装好 Docker 后，三条命令：

```bash
docker pull <你的镜像地址>:latest                       # 或 docker load -i osce-image.tar
docker run -d --name osce -p 3000:3000 -v osce-data:/data --restart unless-stopped \
  -e DEEPSEEK_API_KEY=sk-xxxx -e JWT_SECRET=<随机串> -e ADMIN_PASSWORD='强密码' \
  <你的镜像地址>:latest
# 浏览器打开 http://<机器IP>:3000 ，用 admin / <你设的密码> 登录
```

下面每一步都有细节和排错。

---

## 1. 在目标机器上安装 Docker

| 系统 | 做法 |
|---|---|
| Windows 10/11 | 装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)；若想在 WSL 里用 `docker`，去 Settings → Resources → WSL Integration 打开对应发行版 |
| macOS | 装 Docker Desktop（Intel 芯片选 Intel 版，Apple 芯片选 Apple Silicon 版） |
| Linux 服务器 | `curl -fsSL https://get.docker.com \| sh`，然后 `sudo usermod -aG docker $USER` 并重新登录；`docker compose version` 应可用 |

验证：

```bash
docker version          # 能看到 Client 和 Server 两段
docker run --rm hello-world
```

> **Windows 用户注意**：命令在 **PowerShell** 或 **WSL** 里执行都可以，但路径写法不同。下文命令是通用 bash 写法。

---

## 2. 把镜像弄到目标机器（三选一）

### 方式 A：从镜像仓库拉（最推荐，适合有网）

在**你现在的机器**上推一次：

```bash
docker tag osce:latest <你的账号>/osce:0.1.0
docker login
docker push <你的账号>/osce:0.1.0
```

目标机器上：

```bash
docker pull <你的账号>/osce:0.1.0
docker tag <你的账号>/osce:0.1.0 osce:latest     # 后面命令统一用 osce:latest
```

### 方式 B：离线拷贝（内网 / 没网 / U 盘）

在**有镜像的机器**上导出（实测 tar 约 **95 MB**，gzip 后约 94 MB）：

```bash
docker save osce:latest | gzip > osce-image.tar.gz
```

拷到目标机器后导入：

```bash
gunzip -c osce-image.tar.gz | docker load
docker images osce:latest        # 应看到 406MB
```

> 已实测 `docker save` → `docker load` 往返成功。
> 若 `docker load` 报 manifest 相关错误，改用 `docker save osce:latest -o osce-image.tar` 再 `docker load -i osce-image.tar`。

### 方式 C：在目标机器上从源码构建

需要网络（拉 npm/pip 依赖）：

```bash
git clone <仓库地址> && cd BRIDGE
docker build -f docker/Dockerfile -t osce:latest .
```

---

## 3. 启动容器

### 3.1 最小可用（先跑通）

```bash
docker run -d --name osce -p 3000:3000 -v osce-data:/data --restart unless-stopped osce:latest
```

这样能跑起来，但：**AI 走内置 Mock**（固定话术）、管理员密码是默认的 `admin/admin123`、JWT 用公开默认密钥。只适合先验证。

### 3.2 推荐启动（正式部署）

```bash
docker run -d --name osce \
  -p 3000:3000 \
  -e DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx \
  -e JWT_SECRET="$(openssl rand -hex 32)" \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD='换成一个强密码' \
  -e TZ=Asia/Shanghai \
  -v osce-data:/data \
  --restart unless-stopped \
  osce:latest
```

Windows PowerShell 里没有 `openssl`，把 `$(openssl rand -hex 32)` 换成随便一串 64 位十六进制字符即可。

### 3.3 服务器上更推荐：docker compose

新建目录，放两个文件。

`.env`：

```dotenv
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
JWT_SECRET=换成你自己的64位随机串
ADMIN_USERNAME=admin
ADMIN_PASSWORD=换成一个强密码
TZ=Asia/Shanghai
```

`docker-compose.yml`：

```yaml
services:
  osce:
    image: osce:latest
    container_name: osce
    ports:
      - "3000:3000"
    environment:
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:-}
      DEEPSEEK_BASE_URL: ${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
      DEEPSEEK_MODEL: ${DEEPSEEK_MODEL:-deepseek-v4-flash}
      JWT_SECRET: ${JWT_SECRET:?必须设置 JWT_SECRET}
      ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:?必须设置 ADMIN_PASSWORD}
      TZ: ${TZ:-Asia/Shanghai}
    volumes:
      - osce-data:/data
    restart: unless-stopped

volumes:
  osce-data:
```

启动 / 停止：

```bash
docker compose up -d          # 启动
docker compose logs -f        # 看日志
docker compose down           # 停止（数据保留在 volume 里）
docker compose up -d          # 再启动
```

### 3.4 环境变量一览

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 空 | 不设 → AI 走内置 Mock（功能可用，但回答是固定话术） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容端点 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名 |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | — | 上面三个的别名，二者取其一 |
| `JWT_SECRET` | `dev-secret-change-me` | **正式部署必须改**，否则 token 可被伪造 |
| `ADMIN_USERNAME` | `admin` | 只在**首次初始化空数据库**时生效 |
| `ADMIN_PASSWORD` | `admin123` | 同上；之后改这个变量不会改已有密码 |
| `LLM_MOCK` | 空 | `1` = 强制 Mock（仅测试用） |
| `TZ` | 容器默认 UTC | 设 `Asia/Shanghai` 让会话时间戳是本地时间 |
| `OSCE_DB_PATH` | `/data/osce.db` | 镜像已设好，一般不用动 |
| `GUNICORN_WORKERS` / `_THREADS` / `_TIMEOUT` | `2` / `4` / `180` | 后端并发调参；timeout 必须 > 90（LLM 单次调用上限） |

> AI 模型也可以不用环境变量：用 admin 登录 → **管理后台 → 大模型管理** 里配置，配置存在数据库里，**优先级高于环境变量**。

### 3.5 端口冲突

宿主机 3000 被占用时换一个（容器内始终是 3000）：

```bash
docker run -d --name osce -p 8080:3000 -v osce-data:/data ... osce:latest
# 访问 http://<机器IP>:8080
```

### 3.6 ARM 机器（Apple Silicon / ARM 服务器）

当前镜像是 **linux/amd64**。在 ARM 上直接跑会报 `exec format error` 或只能靠模拟。两个办法：

```bash
# 办法一：用模拟运行（能跑，但慢）
docker run --platform linux/amd64 ... osce:latest

# 办法二（推荐）：在 ARM 机器上重新构建一个 arm64 镜像
docker buildx build --platform linux/arm64 -f docker/Dockerfile -t osce:latest --load .
```

---

## 4. 验证部署成功

```bash
# 1) 容器在跑且健康
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect --format '{{.State.Health.Status}}' osce      # → healthy

# 2) 健康检查接口（经前端代理到后端）
curl http://127.0.0.1:3000/api/health
#   配了 key：{"status":"ok","llm":{"mode":"real","model":"deepseek-v4-flash",...}}
#   没配 key：{"status":"ok","llm":{"mode":"mock",...}}

# 3) 首页
curl -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/

# 4) 数据卷
docker exec osce ls -l /data          # 应有 osce.db
```

浏览器打开 `http://<机器IP>:3000`，用 `admin` / 你设的密码登录；后台里应能看到 13 个内置病例。

> 首次启动约 8 秒进入 healthy（要先建库 + 种子数据），期间页面可能打不开，属正常。

---

## 5. 日常运维

```bash
docker logs -f osce                 # 实时日志（后端 access log + Nitro 日志）
docker restart osce                 # 重启
docker stop osce                    # 停止（数据保留）
docker start osce                   # 再启动
docker stats osce                   # 资源占用
```

### 备份数据

```bash
# 在线安全备份（SQLite 官方推荐用 .backup，避免拷到写一半的库）
docker exec osce python -c "import sqlite3;sqlite3.connect('/data/osce.db').execute('VACUUM INTO \"/data/backup.db\"')"
docker cp osce:/data/backup.db ./osce-backup-$(date +%F).db

# 或者简单粗暴（先停容器）
docker stop osce && docker cp osce:/data/osce.db ./osce-backup.db && docker start osce
```

### 恢复数据

```bash
docker stop osce
docker cp ./osce-backup.db osce:/data/osce.db
docker start osce
```

### 升级到新镜像

```bash
docker pull <镜像地址>:latest        # 或 docker load -i 新的 tar
docker stop osce && docker rm osce
docker run -d --name osce -p 3000:3000 -v osce-data:/data ... <镜像地址>:latest
```

**卷 `osce-data` 不要删**，数据、病例、会话记录都在里面。删卷 = 清库。

### 改环境变量

环境变量是启动时注入的，改了必须**重建容器**：

```bash
docker stop osce && docker rm osce
docker run -d --name osce ... <新的环境变量> ... osce:latest
```

（compose 用户直接 `docker compose up -d`，它会用新配置重建。）

---

## 6. 可选：域名 + HTTPS（反向代理）

容器本身只提供 HTTP。要上域名/证书，在前面放一个反向代理，只暴露 80/443，把 3000 收回本机。

**Caddy（最简单，自动申请证书）**：

```caddyfile
osce.example.com {
    reverse_proxy 127.0.0.1:3000
}
```

**nginx**：

```nginx
server {
    listen 443 ssl http2;
    server_name osce.example.com;
    ssl_certificate     /etc/letsencrypt/live/osce.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/osce.example.com/privkey.pem;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # LLM 回答最长约 90 秒，读超时要放大
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

此时启动容器改成只绑本机：

```bash
docker run -d --name osce -p 127.0.0.1:3000:3000 ... osce:latest
```

> 临时演示也可以用 ngrok：`ngrok http 3000`，前端和 `/api` 共用这一个公网入口（这是本项目原本的设计）。

---

## 7. 排错速查

| 现象 | 原因 | 处理 |
|---|---|---|
| 容器 `unhealthy` / 反复重启 | 首次启动还没建完库，或端口/权限问题 | `docker logs osce` 看报错；首次等 30 秒再看 |
| 页面打得开但接口 502 / 500 | 后端 gunicorn 挂了 | `docker logs osce \| grep -i error`；确认 `--timeout` 没被改小 |
| AI 回答永远是同一套固定话术 | 没配 `DEEPSEEK_API_KEY`（走了 Mock） | 设 key 后重建容器；或在后台「大模型管理」里配 |
| 重启/重建容器后病例和会话没了 | 没挂数据卷 | 加 `-v osce-data:/data`，然后重新初始化 |
| `exec format error` | 在 ARM 机器跑 amd64 镜像 | 加 `--platform linux/amd64` 或按 §3.6 重建 arm64 镜像 |
| 端口被占用 `bind: address already in use` | 宿主机 3000 已有人用 | `-p 8080:3000` 换端口 |
| 时间戳比本地差 8 小时 | 容器默认 UTC | 加 `-e TZ=Asia/Shanghai` |
| 改了 `ADMIN_PASSWORD` 但登录还是老密码 | 管理员只在**空库首次**种子 | 用当前密码登录后到「个人中心」改密，或删卷重新初始化 |
| 浏览器能开但 AI 请求超时 | 反向代理读超时太短 | nginx 加 `proxy_read_timeout 300s` |

---

## 8. 上线前安全清单

- [ ] `JWT_SECRET` 换成随机串（默认值是公开的 `dev-secret-change-me`）
- [ ] `ADMIN_PASSWORD` 换成强密码（默认 `admin123`）
- [ ] 只暴露 3000 给反向代理，不要直接对公网开放，**更不要**暴露后端 5000（镜像里它只绑容器回环，天然不可达）
- [ ] 需要公网访问时上 HTTPS
- [ ] 定期备份 `/data/osce.db`
- [ ] 已知待办（来自仓库 `progress.md`）：收紧 CORS（当前 `origins: "*"`）

---

## 附：这个镜像里到底是什么

```
容器内：
  gunicorn  →  127.0.0.1:5000   Flask 后端（仅容器内可达）
  node      →  0.0.0.0:3000     Nuxt/Nitro 前端 + /api 反向代理（唯一对外入口）
  数据      →  /data/osce.db    SQLite（挂 volume 持久化）
```

浏览器访问 `/api/...` → Nitro 转发到 `127.0.0.1:5000` → Flask。所以对外只需要一个 3000 端口。

架构细节与实测数据见仓库 `docs/docker-deployment.md`；构建文件是 `docker/Dockerfile` 与 `docker/entrypoint.sh`。
