# Tech stack: FastAPI + React (shadcn/ui), SQLite dev -> PostgreSQL prod

We build the backend with Python/FastAPI and the frontend with React + TypeScript + Vite + shadcn/ui (Tailwind), with SQLAlchemy + Alembic over SQLite in development and PostgreSQL in production. The deepest logic — AI scoring, the CCE station state machine, investigation-result matching, and rubric prompts — lives in Python because the AI ecosystem and the maintainer's Python familiarity make it readable and maintainable there; the frontend is React because the chat-heavy station UI needs a component-based SPA, and JavaScript is required there regardless of backend choice.

Considered and rejected: Next.js full-stack (puts the deepest backend logic in a language the maintainer does not yet read, without removing any frontend JavaScript) and full-Python server rendering (chat and multi-panel station UX become significantly harder to build).
