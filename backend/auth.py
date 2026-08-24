from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from database import now_iso

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 7 * 24


def user_to_dict(user) -> dict:
    return {
        "userId": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "phone": user["phone"],
        "realName": user["real_name"],
        "avatar": user["avatar"],
        "role": user["role"],
        "createdAt": user["created_at"],
        "updatedAt": user["updated_at"],
    }


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"message": "请先登录"}), 401

        token = header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "登录已过期，请重新登录"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "登录状态无效，请重新登录"}), 401

        user = g.db.execute(
            "SELECT * FROM users WHERE user_id = ?", (int(payload["sub"]),)
        ).fetchone()
        if user is None:
            return jsonify({"message": "用户不存在"}), 401

        g.user = user
        return fn(*args, **kwargs)

    return wrapper


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"message": "用户名至少3个字符"}), 400
    if len(password) < 6:
        return jsonify({"message": "密码至少6个字符"}), 400

    exists = g.db.execute(
        "SELECT user_id FROM users WHERE username = ?", (username,)
    ).fetchone()
    if exists:
        return jsonify({"message": "用户名已存在"}), 409

    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    real_name = (data.get("realName") or data.get("real_name") or "").strip() or None

    cursor = g.db.execute(
        """
        INSERT INTO users (username, password_hash, email, phone, real_name, role)
        VALUES (?, ?, ?, ?, ?, 'student')
        """,
        (username, generate_password_hash(password), email, phone, real_name),
    )
    g.db.commit()

    user = g.db.execute(
        "SELECT * FROM users WHERE user_id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify({"token": create_token(user["user_id"]), "user": user_to_dict(user)}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = g.db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"message": "用户名或密码错误"}), 401

    return jsonify({"token": create_token(user["user_id"]), "user": user_to_dict(user)})


@bp.get("/me")
@token_required
def me():
    return jsonify({"user": user_to_dict(g.user)})


@bp.put("/me")
@token_required
def update_me():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    real_name = (data.get("realName") or data.get("real_name") or "").strip() or None
    avatar = (data.get("avatar") or "").strip() or None

    g.db.execute(
        """
        UPDATE users
        SET email = ?, phone = ?, real_name = ?, avatar = ?, updated_at = ?
        WHERE user_id = ?
        """,
        (email, phone, real_name, avatar, now_iso(), g.user["user_id"]),
    )
    g.db.commit()

    user = g.db.execute(
        "SELECT * FROM users WHERE user_id = ?", (g.user["user_id"],)
    ).fetchone()
    return jsonify({"user": user_to_dict(user)})


@bp.put("/password")
@token_required
def change_password():
    data = request.get_json(silent=True) or {}
    old_password = data.get("oldPassword") or ""
    new_password = data.get("newPassword") or ""

    if not check_password_hash(g.user["password_hash"], old_password):
        return jsonify({"message": "当前密码不正确"}), 400
    if len(new_password) < 6:
        return jsonify({"message": "新密码至少6个字符"}), 400

    g.db.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?",
        (generate_password_hash(new_password), now_iso(), g.user["user_id"]),
    )
    g.db.commit()
    return jsonify({"message": "密码修改成功"})

def admin_required(fn):
    @wraps(fn)
    @token_required
    def wrapper(*args, **kwargs):
        if g.user["role"] != "admin":
            return jsonify({"message": "需要管理员权限"}), 403
        return fn(*args, **kwargs)

    return wrapper
