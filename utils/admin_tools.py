import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _get_conn():
    """اتصال sync به دیتابیس"""
    import psycopg2
    from config import DATABASE_URL
    sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(sync_url)


# ============================================================
# 📊 آمار کلی
# ============================================================
def get_general_stats() -> dict:
    conn = _get_conn()
    cur = conn.cursor()
    stats = {}
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        stats["total_users"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")
        stats["banned_users"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '24 hours'"
        )
        stats["active_24h"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '7 days'"
        )
        stats["active_7d"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM operations")
        stats["total_ops"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM operations WHERE created_at::date = CURRENT_DATE"
        )
        stats["ops_today"] = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM operations WHERE created_at > NOW() - INTERVAL '7 days'"
        )
        stats["ops_7d"] = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(file_size), 0) FROM operations")
        total_bytes = cur.fetchone()[0]
        stats["total_size_mb"] = total_bytes / (1024 * 1024)

        return stats
    finally:
        cur.close()
        conn.close()


# ============================================================
# 🏆 کاربران برتر
# ============================================================
def get_top_users(limit: int = 10) -> list:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT u.id, u.first_name, u.username, COUNT(o.id) as op_count
            FROM users u
            LEFT JOIN operations o ON u.id = o.user_id
            GROUP BY u.id, u.first_name, u.username
            ORDER BY op_count DESC
            LIMIT %s
            """,
            (limit,)
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# ============================================================
# 📈 آمار عملیات
# ============================================================
def get_operations_breakdown() -> list:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT operation_type, COUNT(*) as count
            FROM operations
            GROUP BY operation_type
            ORDER BY count DESC
            LIMIT 20
            """
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# ============================================================
# 👥 لیست کاربران
# ============================================================
def get_all_user_ids(include_banned: bool = False) -> list:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        if include_banned:
            cur.execute("SELECT id FROM users")
        else:
            cur.execute("SELECT id FROM users WHERE is_banned = FALSE")
        return [row[0] for row in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


# ============================================================
# 👤 اطلاعات کاربر (با ID)
# ============================================================
def get_user_info(user_id: int) -> dict | None:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, first_name, username, joined_at, last_active, is_banned
            FROM users WHERE id = %s
            """,
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None

        cur.execute(
            "SELECT COUNT(*) FROM operations WHERE user_id = %s",
            (user_id,)
        )
        op_count = cur.fetchone()[0]

        return {
            "id": row[0],
            "first_name": row[1],
            "username": row[2],
            "joined_at": row[3],
            "last_active": row[4],
            "is_banned": row[5],
            "op_count": op_count,
        }
    finally:
        cur.close()
        conn.close()


# ============================================================
# 👤 اطلاعات کاربر (با یوزرنیم)
# ============================================================
def get_user_info_by_username(username: str) -> dict | None:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        username = username.lstrip("@")

        cur.execute(
            """
            SELECT id, first_name, username, joined_at, last_active, is_banned
            FROM users
            WHERE LOWER(username) = LOWER(%s)
            LIMIT 1
            """,
            (username,)
        )
        row = cur.fetchone()
        if not row:
            return None

        user_id = row[0]
        cur.execute(
            "SELECT COUNT(*) FROM operations WHERE user_id = %s",
            (user_id,)
        )
        op_count = cur.fetchone()[0]

        return {
            "id": row[0],
            "first_name": row[1],
            "username": row[2],
            "joined_at": row[3],
            "last_active": row[4],
            "is_banned": row[5],
            "op_count": op_count,
        }
    finally:
        cur.close()
        conn.close()


# ============================================================
# 🚫 بن/آنبن
# ============================================================
def ban_user(user_id: int, banned: bool = True) -> bool:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET is_banned = %s WHERE id = %s",
            (banned, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.exception(f"خطا در بن: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def ban_user_by_username(username: str, banned: bool = True) -> bool:
    """بن/آنبن با یوزرنیم"""
    info = get_user_info_by_username(username)
    if not info:
        return False
    return ban_user(info["id"], banned)


def is_user_banned(user_id: int) -> bool:
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT is_banned FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return bool(row and row[0])
    except Exception:
        return False
    finally:
        cur.close()
        conn.close()


# ============================================================
# 📝 ثبت کاربر
# ============================================================
def register_user(user_id: int, first_name: str, username: str):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (id, first_name, username)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET first_name = EXCLUDED.first_name,
                username = EXCLUDED.username,
                last_active = NOW()
            """,
            (user_id, first_name, username)
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"خطا در ثبت کاربر: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def update_last_active(user_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET last_active = NOW() WHERE id = %s", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close()
        conn.close()


# ============================================================
# 📥 خروجی CSV
# ============================================================
def export_users_csv() -> str | None:
    import csv
    import os
    import uuid
    from config import TEMP_DIR

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT u.id, u.first_name, u.username, u.joined_at, u.last_active,
                   u.is_banned, COUNT(o.id) as op_count
            FROM users u
            LEFT JOIN operations o ON u.id = o.user_id
            GROUP BY u.id, u.first_name, u.username, u.joined_at, u.last_active, u.is_banned
            ORDER BY u.joined_at DESC
            """
        )
        rows = cur.fetchall()

        output = os.path.join(TEMP_DIR, f"users_{uuid.uuid4().hex[:8]}.csv")
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "First Name", "Username", "Joined At",
                "Last Active", "Banned", "Op Count"
            ])
            for row in rows:
                writer.writerow(row)

        return output
    except Exception as e:
        logger.exception(f"خطا در CSV: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def export_operations_csv() -> str | None:
    import csv
    import os
    import uuid
    from config import TEMP_DIR

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, user_id, operation_type, input_format, output_format,
                   file_size, status, created_at
            FROM operations
            ORDER BY created_at DESC
            LIMIT 10000
            """
        )
        rows = cur.fetchall()

        output = os.path.join(TEMP_DIR, f"ops_{uuid.uuid4().hex[:8]}.csv")
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "User ID", "Type", "Input", "Output",
                "Size", "Status", "Created At"
            ])
            for row in rows:
                writer.writerow(row)

        return output
    except Exception as e:
        logger.exception(f"خطا در CSV: {e}")
        return None
    finally:
        cur.close()
        conn.close()