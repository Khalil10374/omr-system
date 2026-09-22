"""
Database Manager for OMR Barcode & QR Code Print System
Handles SQLite database operations: authentication, settings, generation history, and analytics.
"""

import sqlite3
import os
import hashlib
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "omr_system.db")

def hash_password(password: str) -> str:
    """Returns SHA-256 hash of the password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables and default data if not already present."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # System settings table (key-value store)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Generation history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            start_roll TEXT NOT NULL,
            end_roll TEXT NOT NULL,
            sheet_count INTEGER NOT NULL,
            print_mode TEXT NOT NULL,
            qr3_included INTEGER DEFAULT 0,
            filename TEXT NOT NULL,
            file_size_kb REAL DEFAULT 0.0,
            created_by TEXT DEFAULT 'admin'
        )
    """)

    # Code records table for individual sheets
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id INTEGER,
            roll_number TEXT NOT NULL,
            binary_code TEXT NOT NULL,
            hex_suffix TEXT NOT NULL,
            qr_payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(history_id) REFERENCES generation_history(id) ON DELETE CASCADE
        )
    """)

    # Create default admin user if none exists
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        default_pwd_hash = hash_password("admin123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", default_pwd_hash, "admin")
        )

    # Set default settings if not exists
    default_settings = {
        "app_name": "OMR Barcode & QR Code Print System",
        "app_subtitle": "Madrasah & Academic Board OMR Sheet Solution",
        "logo_path": "",
        "theme_color": "#1e40af",
        "default_roll": "2512100077",
        "default_sheets": "5",
        "default_offset_x_mm": "0.2",
        "default_offset_y_mm": "0.8",
        "next_barcode_sequence": "0"
    }
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


def allocate_barcode_sequence(count: int) -> int:
    """Reserve a globally unique range of 30-bit barcode payload IDs."""
    try:
        requested = int(count)
    except (TypeError, ValueError) as exc:
        raise ValueError("Barcode sequence count must be an integer.") from exc

    if requested < 1:
        raise ValueError("Barcode sequence count must be at least 1.")

    # The first and last OMR cells are fixed markers, leaving 30 data bits.
    max_sequence = (1 << 30) - 1
    init_db()
    conn = get_connection()

    try:
        # Serialize allocation so two simultaneous Streamlit sessions cannot
        # receive the same barcode payload range.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT value FROM system_settings WHERE key = ?",
            ("next_barcode_sequence",)
        ).fetchone()
        start = int(row["value"]) if row and row["value"] else 0

        if start < 0 or start + requested - 1 > max_sequence:
            raise ValueError(
                f"Only {max_sequence + 1:,} unique fixed-marker barcode IDs are available."
            )

        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)",
            ("next_barcode_sequence", str(start + requested))
        )
        conn.commit()
        return start
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ----------------- User Authentication & Management ----------------- #

def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifies username and password. Returns user dict if valid, else None."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    p_hash = hash_password(password)
    cursor.execute("SELECT id, username, role, created_at FROM users WHERE username = ? AND password_hash = ?", (username, p_hash))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_user_credentials(current_username: str, new_username: Optional[str] = None, new_password: Optional[str] = None) -> Tuple[bool, str]:
    """Updates username and/or password for an existing user."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (current_username,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return False, "User not found."

    user_id = user_row["id"]
    try:
        if new_username and new_username != current_username:
            cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (new_username, user_id))
            if cursor.fetchone():
                conn.close()
                return False, "Username already exists. Please choose a different one."
            cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user_id))

        if new_password:
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), user_id))

        conn.commit()
        conn.close()
        return True, "Credentials updated successfully!"
    except Exception as e:
        conn.close()
        return False, str(e)

# ----------------- Settings Management ----------------- #

def get_setting(key: str, default: str = "") -> str:
    """Retrieves a setting value."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row and row["value"] is not None else default

def set_setting(key: str, value: str):
    """Sets or updates a setting value."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_login_banner() -> str:
    """Returns path to the active login left banner image."""
    custom = get_setting("login_banner_path", "")
    if custom and os.path.exists(custom):
        return custom
    banner = os.path.join(BASE_DIR, "login_banner.png")
    if os.path.exists(banner):
        return banner
    return os.path.join(BASE_DIR, "default_login_banner.png")

def set_login_banner(path: str):
    set_setting("login_banner_path", path)

def reset_login_banner():
    set_setting("login_banner_path", "")

def get_login_bg() -> str:
    """Returns path to the active login full-screen background wallpaper."""
    custom = get_setting("login_bg_path", "")
    if custom and os.path.exists(custom):
        return custom
    background = os.path.join(BASE_DIR, "login_bg.png")
    if os.path.exists(background):
        return background
    return ""

def set_login_bg(path: str):
    set_setting("login_bg_path", path)

def reset_login_bg():
    set_setting("login_bg_path", "")

# ----------------- History & Batch Records ----------------- #

def add_generation_batch(
    start_roll: str,
    end_roll: str,
    sheet_count: int,
    print_mode: str,
    qr3_included: bool,
    filename: str,
    file_size_kb: float,
    created_by: str,
    items_meta: Optional[List[Dict[str, Any]]] = None
) -> int:
    """Adds a newly generated batch to database history."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO generation_history 
        (timestamp, start_roll, end_roll, sheet_count, print_mode, qr3_included, filename, file_size_kb, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_str,
        str(start_roll),
        str(end_roll),
        int(sheet_count),
        print_mode,
        1 if qr3_included else 0,
        filename,
        round(file_size_kb, 2),
        created_by
    ))
    history_id = cursor.lastrowid

    if items_meta:
        for item in items_meta:
            cursor.execute("""
                INSERT INTO code_records
                (history_id, roll_number, binary_code, hex_suffix, qr_payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                history_id,
                str(item.get("roll", "")),
                str(item.get("binary", "")),
                str(item.get("hex", "")),
                str(item.get("qr_payload", "")),
                now_str
            ))

    conn.commit()
    conn.close()
    return history_id

def get_history(
    search_query: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    print_mode: Optional[str] = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """Fetches generation history with search and date filters."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM generation_history WHERE 1=1"
    params = []

    if search_query and search_query.strip():
        q = f"%{search_query.strip()}%"
        query += " AND (start_roll LIKE ? OR end_roll LIKE ? OR filename LIKE ? OR created_by LIKE ?)"
        params.extend([q, q, q, q])

    if start_date:
        query += " AND date(timestamp) >= ?"
        params.append(start_date.strftime("%Y-%m-%d"))

    if end_date:
        query += " AND date(timestamp) <= ?"
        params.append(end_date.strftime("%Y-%m-%d"))

    if print_mode and print_mode != "All":
        query += " AND print_mode LIKE ?"
        params.append(f"%{print_mode}%")

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_batch_records(history_id: int) -> List[Dict[str, Any]]:
    """Gets all code records for a specific batch."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM code_records WHERE history_id = ? ORDER BY id ASC", (history_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_history_item(history_id: int) -> bool:
    """Deletes a history item and related code records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM code_records WHERE history_id = ?", (history_id,))
    cursor.execute("DELETE FROM generation_history WHERE id = ?", (history_id,))
    conn.commit()
    conn.close()
    return True

def clear_all_history() -> bool:
    """Clears all history records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM code_records")
    cursor.execute("DELETE FROM generation_history")
    conn.commit()
    conn.close()
    return True

# ----------------- Dashboard Analytics ----------------- #

def get_dashboard_stats() -> Dict[str, Any]:
    """Calculates summary statistics for dashboard."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # Total batches
    cursor.execute("SELECT COUNT(*) as count FROM generation_history")
    total_batches = cursor.fetchone()["count"]

    # Total sheets
    cursor.execute("SELECT COALESCE(SUM(sheet_count), 0) as total FROM generation_history")
    total_sheets = cursor.fetchone()["total"]

    # Today's sheets & batches
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) as batches, COALESCE(SUM(sheet_count), 0) as sheets FROM generation_history WHERE date(timestamp) = ?", (today_str,))
    today_row = cursor.fetchone()
    today_batches = today_row["batches"]
    today_sheets = today_row["sheets"]

    # Latest batch info
    cursor.execute("SELECT * FROM generation_history ORDER BY id DESC LIMIT 1")
    latest_row = cursor.fetchone()
    latest_batch = dict(latest_row) if latest_row else None

    # Print mode breakdown
    cursor.execute("""
        SELECT print_mode, COUNT(*) as batch_count, COALESCE(SUM(sheet_count), 0) as sheets_count 
        FROM generation_history 
        GROUP BY print_mode
    """)
    mode_breakdown = [dict(r) for r in cursor.fetchall()]

    # Daily trends (last 10 active days)
    cursor.execute("""
        SELECT date(timestamp) as gen_date, COUNT(*) as batch_count, SUM(sheet_count) as sheet_count
        FROM generation_history
        GROUP BY date(timestamp)
        ORDER BY gen_date DESC
        LIMIT 10
    """)
    trends = [dict(r) for r in cursor.fetchall()]
    trends.reverse()

    conn.close()

    return {
        "total_batches": total_batches,
        "total_sheets": total_sheets,
        "today_batches": today_batches,
        "today_sheets": today_sheets,
        "latest_batch": latest_batch,
        "mode_breakdown": mode_breakdown,
        "trends": trends
    }
