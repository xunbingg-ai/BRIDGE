# OSCE 学生端训练平台

一个面向医学生的 OSCE 问诊训练项目，前端使用 Nuxt 4 + Pinia + Tailwind CSS，后端使用 Flask + SQLite。项目按 `frontend/` 和 `backend/` 分离。

## 目录结构

```
OSCE/
├── frontend/                # Nuxt 4 前端
│   ├── app/
│   │   ├── components/
│   │   │   ├── Index/       # NavBar / CaseBox / SearchBox
│   │   │   ├── Session/     # ChatContainer / ChatBox / InputBox
│   │   │   ├── Dashboard/   # ProfileBox / HistoryBox / ChangeInfoBox / ChangePwdBox
│   │   │   ├── Report/      # ScoreBox / AnswerBox
│   │   │   └── Public/      # AppBar
│   │   ├── pages/           # index / login / register / dashboard / session / report
│   │   ├── stores/          # Pinia stores
│   │   └── composables/     # API 封装
│   ├── nuxt.config.ts
│   └── package.json
└── backend/                 # Flask 后端
    ├── app.py               # Flask 应用入口
    ├── schema.sql           # SQLite 表结构
    ├── seed_data.py         # 内置 12 个演示病例
    ├── ai_service.py        # AI 病人/考官/评分，含 Mock 降级
    ├── auth.py              # 注册、登录、个人信息、改密
    ├── cases.py             # 病例列表与详情
    ├── sessions.py          # 会话、消息、提交、评分轮询
    └── requirements.txt
```

## 已实现功能

- `/`：首页展示病例，支持七个门类筛选和关键词搜索，病例卡片懒加载。
- `/login` 与 `/register`：学生注册登录，JWT 鉴权。
- `/dashboard`：左侧 `ProfileBox`，右侧 `HistoryBox`。
- `/session/{sessionid}`：8 分钟倒计时，AI 病人问询 → 结束问询 → AI 考官审查 → 提交审查。
- `/report/{sessionid}`：提交后进入评分中，轮询完成后展示 `ScoreBox` 和 `AnswerBox`。
- `content` 保存完整对话 JSON，`score` 保存总分与四个小分，`report` 保存结构化评价 JSON。
- 未登录可以浏览病例，点击开始练习时跳转登录。

## 快速启动

### 1. 启动后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

后端默认运行在 `http://127.0.0.1:5000`，首次启动会自动创建 `backend/osce.db` 并写入 12 个演示病例。

### 2. 启动前端

```powershell
cd frontend
pnpm install
pnpm dev
```

前端默认运行在 `http://localhost:3000`，并通过 `http://127.0.0.1:5000/api` 访问后端。

### 3. 可选配置

在启动后端前设置环境变量：

```powershell
$env:JWT_SECRET = "please-change-me"
$env:OPENAI_API_KEY = "sk-..."
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_MODEL = "gpt-4o-mini"
```

- 不设置 `OPENAI_API_KEY` 时，系统使用内置 Mock 逻辑，方便本地无密钥演示完整流程。
- 设置后，AI 病人、AI 考官和自动判卷都会走 OpenAI 兼容接口。

前端 API 地址可通过 `.env` 覆盖：

```bash
NUXT_PUBLIC_API_BASE=http://127.0.0.1:5000/api
```

## 数据库表

| 表名 | 作用 |
| --- | --- |
| `users` | 用户账号与个人信息 |
| `cases` | 病例库，含 AI 提示词和参考答案 |
| `sessions` | 每次练习会话，含 `content`、`score`、`report` JSON 字段 |

核心 `sessions` 字段：

- `session_id`
- `user_id`
- `case_id`
- `create_at`
- `deadline_at`
- `status`：`patient` / `examiner` / `scoring` / `completed` / `expired`
- `content`：完整对话 JSON
- `score`：评分 JSON
- `report`：评价报告 JSON

## 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/auth/register` | 注册 |
| `POST` | `/api/auth/login` | 登录 |
| `GET` | `/api/auth/me` | 当前用户 |
| `PUT` | `/api/auth/me` | 修改信息 |
| `PUT` | `/api/auth/password` | 修改密码 |
| `GET` | `/api/cases` | 病例列表与筛选 |
| `GET` | `/api/cases/{caseid}` | 病例详情 |
| `POST` | `/api/sessions` | 创建会话 |
| `POST` | `/api/sessions/{sessionid}/message` | 发送消息 |
| `POST` | `/api/sessions/{sessionid}/end-inquiry` | 结束问询 |
| `POST` | `/api/sessions/{sessionid}/submit` | 提交审查并触发评分 |
| `GET` | `/api/sessions/{sessionid}` | 会话详情/报告 |
| `GET` | `/api/sessions` | 历史练习记录 |
| `GET` | `/api/health` | 健康检查 |

## 说明

- 当前为学生端，管理员端和教师端尚未实现。
- 判卷使用后台线程异步执行，前端 `/report/{sessionid}` 会每 2 秒轮询一次状态。
- 演示病例与 Mock AI 只用于本地开发；生产环境请配置正式模型密钥并替换演示数据。

## 快捷启动脚本

项目根目录提供了两个 Windows 批处理脚本：

- `start-backend.bat`：创建/复用 Python 虚拟环境，安装依赖并启动 Flask 后端。
- `start-frontend.bat`：安装前端依赖（首次）并启动 Nuxt 开发服务器。

两个脚本需分别打开两个终端窗口运行。

## 管理员账号

首次启动数据库时自动创建默认管理员：

- 用户名：`admin`
- 密码：`admin123`

可通过环境变量覆盖：

```powershell
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "admin123"
```

登录后导航栏会显示“管理后台”，访问 `/admin` 可管理病例和模型配置。

## 管理员接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/admin/cases` | 获取全部病例 |
| `POST` | `/api/admin/cases` | 新增病例 |
| `PUT` | `/api/admin/cases/{caseid}` | 修改病例 |
| `DELETE` | `/api/admin/cases/{caseid}` | 删除单个病例 |
| `POST` | `/api/admin/cases/batch-delete` | 批量删除病例 |
| `GET` | `/api/admin/cases/template.csv` | 下载 CSV 模板 |
| `POST` | `/api/admin/cases/import` | 上传 CSV 批量导入 |
| `GET` | `/api/admin/llm-config` | 获取模型配置 |
| `PUT` | `/api/admin/llm-config` | 保存模型配置 |
| `POST` | `/api/admin/llm-config/models` | 获取模型列表 |
| `POST` | `/api/admin/llm-config/test` | 测试模型响应速度 |
