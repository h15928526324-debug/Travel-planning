"""
积分管理服务 — SQLite 持久化存储

每个用户由 session_id 标识，拥有独立积分账户。
积分用于生成旅行方案，每次规划消耗固定积分。
"""

from __future__ import annotations

import sqlite3
import uuid
import threading
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "credits.db"

# 线程锁：SQLite 单写，多线程并发时需要
_lock = threading.Lock()

# ── 积分定价 ──
PLAN_COST = 10           # 生成一次旅行方案消耗 10 积分
INITIAL_CREDITS = 30     # 新用户注册赠送 30 积分（3 次免费）

RECHARGE_PLANS = [
    {"id": "plan_99",  "name": "体验包",   "price": 9.9,   "credits": 50,   "badge": "🎫"},
    {"id": "plan_199", "name": "畅游包",   "price": 19.9,  "credits": 120,  "badge": "🌟"},
    {"id": "plan_499", "name": "无限包",   "price": 49.9,  "credits": 350,  "badge": "👑"},
]


def _get_connection() -> sqlite3.Connection:
    """获取数据库连接（自动创建目录和表）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")       # 并发读友好
    conn.execute("PRAGMA busy_timeout=3000")      # 3 秒忙等待
    return conn


def _init_db(conn: sqlite3.Connection):
    """初始化数据库表"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            credits INTEGER NOT NULL DEFAULT 0,
            total_recharged INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('init', 'recharge', 'consume', 'refund', 'gift')),
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_session ON users(session_id);
        CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id);
    """)


class CreditManager:
    """
    积分管理器 — 每个 session_id 对应一个独立账户

    用法:
        cm = CreditManager(session_id="abc123")
        cm.balance          # 当前积分
        cm.deduct(10, "生成成都2日游方案")  # 扣费
        cm.recharge(50, "充值 9.9 元")       # 充值
        cm.history()        # 交易记录
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._user_id: int | None = None
        self._ensure_user()

    def _ensure_user(self):
        """确保用户存在，不存在则创建并赠送初始积分"""
        with _lock:
            conn = _get_connection()
            _init_db(conn)

            row = conn.execute(
                "SELECT id, credits FROM users WHERE session_id = ?",
                (self.session_id,)
            ).fetchone()

            if row:
                self._user_id = row["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO users (session_id, credits) VALUES (?, ?)",
                    (self.session_id, INITIAL_CREDITS)
                )
                self._user_id = cur.lastrowid
                # 记录初始赠送
                conn.execute(
                    "INSERT INTO transactions (user_id, type, amount, balance_after, description) "
                    "VALUES (?, 'init', ?, ?, '🎁 新用户注册赠送')",
                    (self._user_id, INITIAL_CREDITS, INITIAL_CREDITS)
                )
                conn.commit()
            conn.close()

    @property
    def balance(self) -> int:
        """当前积分余额"""
        conn = _get_connection()
        row = conn.execute(
            "SELECT credits FROM users WHERE id = ?", (self._user_id,)
        ).fetchone()
        conn.close()
        return row["credits"] if row else 0

    @property
    def total_recharged(self) -> int:
        """累计充值金额"""
        conn = _get_connection()
        row = conn.execute(
            "SELECT total_recharged FROM users WHERE id = ?", (self._user_id,)
        ).fetchone()
        conn.close()
        return row["total_recharged"] if row else 0

    @property
    def remaining_plans(self) -> int:
        """剩余可生成方案次数"""
        return max(0, self.balance // PLAN_COST)

    def can_plan(self) -> bool:
        """是否还有足够积分生成方案"""
        return self.balance >= PLAN_COST

    def deduct(self, amount: int, description: str = "") -> bool:
        """
        扣减积分。

        Returns:
            True 扣减成功, False 余额不足
        """
        if amount <= 0:
            return True
        if self.balance < amount:
            return False

        with _lock:
            conn = _get_connection()
            new_balance = self.balance - amount
            conn.execute(
                "UPDATE users SET credits = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (new_balance, self._user_id)
            )
            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, balance_after, description) "
                "VALUES (?, 'consume', ?, ?, ?)",
                (self._user_id, -amount, new_balance, description or f"消耗 {amount} 积分")
            )
            conn.commit()
            conn.close()
        return True

    def recharge(self, amount: int, description: str = "") -> int:
        """
        充值积分。

        Returns:
            充值后的余额
        """
        with _lock:
            conn = _get_connection()
            new_balance = self.balance + amount
            conn.execute(
                "UPDATE users SET credits = ?, total_recharged = total_recharged + ?, "
                "updated_at = datetime('now','localtime') WHERE id = ?",
                (new_balance, amount, self._user_id)
            )
            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, balance_after, description) "
                "VALUES (?, 'recharge', ?, ?, ?)",
                (self._user_id, amount, new_balance, description or f"充值 {amount} 积分")
            )
            conn.commit()
            conn.close()
        return new_balance

    def history(self, limit: int = 20) -> list[dict]:
        """最近的交易记录"""
        conn = _get_connection()
        rows = conn.execute(
            "SELECT type, amount, balance_after, description, created_at "
            "FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (self._user_id, limit)
        ).fetchall()
        conn.close()

        type_labels = {"init": "🎁", "recharge": "💳", "consume": "✈️", "refund": "↩️", "gift": "🎁"}
        return [
            {
                "type": r["type"],
                "icon": type_labels.get(r["type"], "•"),
                "amount": r["amount"],
                "balance_after": r["balance_after"],
                "description": r["description"],
                "time": r["created_at"],
            }
            for r in rows
        ]


# ── 全局单例（按 session_id 缓存实例） ──

_instances: dict[str, CreditManager] = {}


def get_credit_manager(session_id: str) -> CreditManager:
    """获取或创建指定 session 的 CreditManager"""
    if session_id not in _instances:
        _instances[session_id] = CreditManager(session_id)
    return _instances[session_id]
