# app/db/database.py
import sqlite3
import secrets
from contextlib import contextmanager
from typing import Optional, List, Dict
import threading
from datetime import datetime

class DB:
    _instance = None
    _lock = threading.Lock()
    
    @staticmethod
    @contextmanager
    def get_conn():
        """Get a database connection with row factory"""
        conn = sqlite3.connect('app.db', detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    @staticmethod
    def init_db():
        """Initialize the database with the api_keys table"""
        with DB.get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            conn.commit()
    
    @staticmethod
    def create_key(name: str) -> str:
        """Create a new API key"""
        api_key = secrets.token_urlsafe(32)
        with DB.get_conn() as conn:
            conn.execute(
                "INSERT INTO api_keys (key, name) VALUES (?, ?)",
                (api_key, name)
            )
            conn.commit()
        return api_key
    
    @staticmethod
    def verify_key(api_key: str) -> Optional[str]:
        """Verify an API key and update last_used timestamp"""
        with DB.get_conn() as conn:
            result = conn.execute("""
                UPDATE api_keys 
                SET last_used = ? 
                WHERE key = ? AND is_active = TRUE
                RETURNING name
                """, 
                (datetime.utcnow(), api_key)
            ).fetchone()
            conn.commit()
            return result['name'] if result else None
    
    @staticmethod
    def delete_key(api_key: str) -> bool:
        """Delete an API key"""
        with DB.get_conn() as conn:
            cursor = conn.execute("DELETE FROM api_keys WHERE key = ?", (api_key,))
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def list_keys() -> List[Dict]:
        """List all API keys"""
        with DB.get_conn() as conn:
            results = conn.execute("""
                SELECT key, name, created_at, last_used, is_active 
                FROM api_keys
                ORDER BY created_at DESC
            """).fetchall()
            return [dict(row) for row in results]
    
    @staticmethod
    def disable_key(api_key: str) -> bool:
        """Disable an API key without deleting it"""
        with DB.get_conn() as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET is_active = FALSE WHERE key = ?",
                (api_key,)
            )
            conn.commit()
            return cursor.rowcount > 0

# Initialize database when module is imported
DB.init_db()