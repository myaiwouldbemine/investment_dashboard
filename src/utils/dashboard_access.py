"""Signed one-time access gate for dashboard links."""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import time
from pathlib import Path

import streamlit as st

SESSION_KEY = "_dashboard_access_granted"


def _u(text: str) -> str:
    return text.encode("ascii").decode("unicode_escape")


def _get_secret() -> str:
    secret = os.getenv("DASHBOARD_LINK_SECRET", "").strip()
    if secret:
        return secret
    try:
        return str(st.secrets.get("DASHBOARD_LINK_SECRET", "")).strip()
    except Exception:
        return ""


def _get_nonce_db_path() -> str:
    env_value = os.getenv("DASHBOARD_ACCESS_NONCE_DB_PATH", "").strip()
    return env_value or "/tmp/investment_dashboard_access_nonce.sqlite3"


def _read_param(params, key: str) -> str:
    value = params.get(key, "")
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value).strip()


def _consume_nonce_once(db_path: str, nonce: str, expires_at: int, now_epoch: int) -> bool:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS used_dashboard_nonce (
                nonce TEXT PRIMARY KEY,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute("DELETE FROM used_dashboard_nonce WHERE expires_at < ?", (now_epoch,))
        try:
            conn.execute(
                "INSERT INTO used_dashboard_nonce (nonce, expires_at, created_at) VALUES (?, ?, ?)",
                (nonce, expires_at, now_epoch),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def validate_access_params(
    *,
    access_chat: str,
    access_exp: str,
    access_nonce: str,
    access_sig: str,
    secret: str,
    nonce_db_path: str,
    now_epoch: int | None = None,
) -> tuple[bool, str]:
    if not all([access_chat, access_exp, access_nonce, access_sig]):
        return False, _u(r"\u7f3a\u5c11\u5b58\u53d6\u53c3\u6578\uff0c\u8acb\u56de Telegram \u91cd\u65b0\u53d6\u5f97 dashboard \u9023\u7d50\u3002")

    try:
        expires_at = int(access_exp)
    except ValueError:
        return False, _u(r"\u9023\u7d50\u53c3\u6578\u683c\u5f0f\u932f\u8aa4\uff0c\u8acb\u91cd\u65b0\u53d6\u5f97 dashboard \u9023\u7d50\u3002")

    now = int(time.time()) if now_epoch is None else int(now_epoch)
    if expires_at < now:
        return False, _u(r"\u9023\u7d50\u5df2\u904e\u671f\uff0c\u8acb\u56de Telegram \u91cd\u65b0\u53d6\u5f97\u4e00\u6b21\u6027\u9023\u7d50\u3002")

    payload = f"{access_chat}:{expires_at}:{access_nonce}"
    expected_sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, access_sig):
        return False, _u(r"\u9023\u7d50\u7c3d\u7ae0\u9a57\u8b49\u5931\u6557\uff0c\u8acb\u56de Telegram \u91cd\u65b0\u53d6\u5f97\u9023\u7d50\u3002")

    if not _consume_nonce_once(nonce_db_path, access_nonce, expires_at, now):
        return False, _u(r"\u9019\u500b\u9023\u7d50\u5df2\u88ab\u4f7f\u7528\u904e\uff0c\u8acb\u56de Telegram \u53d6\u5f97\u65b0\u9023\u7d50\u3002")

    return True, "ok"


def enforce_dashboard_access() -> None:
    secret = _get_secret()
    if not secret:
        st.error(_u(r"\u5b89\u5168\u8a2d\u5b9a\u4e0d\u5b8c\u6574\uff1a\u7f3a\u5c11 DASHBOARD_LINK_SECRET\uff0c\u5df2\u62d2\u7d55\u5b58\u53d6\u3002"))
        st.stop()

    params = st.query_params
    access_chat = _read_param(params, "access_chat")
    access_exp = _read_param(params, "access_exp")
    access_nonce = _read_param(params, "access_nonce")
    access_sig = _read_param(params, "access_sig")
    has_access_params = any([access_chat, access_exp, access_nonce, access_sig])

    if has_access_params:
        ok, reason = validate_access_params(
            access_chat=access_chat,
            access_exp=access_exp,
            access_nonce=access_nonce,
            access_sig=access_sig,
            secret=secret,
            nonce_db_path=_get_nonce_db_path(),
        )
        if not ok:
            st.error(reason)
            st.stop()

        st.session_state[SESSION_KEY] = True
        try:
            st.query_params.clear()
        except Exception:
            pass
        return

    if st.session_state.get(SESSION_KEY):
        return

    st.error(_u(r"\u8acb\u5f9e Telegram \u6309\u9215\u9032\u5165 dashboard\uff0c\u4e0d\u652f\u63f4\u76f4\u63a5\u958b\u555f\u3002"))
    st.stop()
