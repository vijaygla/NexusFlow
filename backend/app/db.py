"""
NexusFlow Database Persistence Module
Connects to MS SQL Server to log agent workflows, session metrics, and code snapshots.
Provides query interfaces for Session History & Analytics API.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import pyodbc
from app.config import get_settings

logger = logging.getLogger("nexusflow.db")


def init_db() -> bool:
    """Initializes tables and columns in MS SQL Server if enabled."""
    settings = get_settings()
    if not settings.DB_ENABLED:
        logger.info("Database persistence is disabled via config.")
        return False

    try:
        conn = pyodbc.connect(settings.sql_connection_string, autocommit=True)
        cursor = conn.cursor()
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='WorkflowExecutions' AND xtype='U')
        CREATE TABLE WorkflowExecutions (
            Id INT IDENTITY(1,1) PRIMARY KEY,
            SessionId NVARCHAR(100) NOT NULL,
            Prompt NVARCHAR(MAX) NOT NULL,
            Status NVARCHAR(50) NOT NULL,
            Iterations INT NOT NULL DEFAULT 1,
            GeneratedFilesCount INT NOT NULL DEFAULT 0,
            ReviewFeedback NVARCHAR(MAX) NULL,
            GeneratedFilesJson NVARCHAR(MAX) NULL,
            CreatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE()
        );
        """
        cursor.execute(create_table_sql)

        # Check if GeneratedFilesJson column exists in case table was created earlier
        add_col_sql = """
        IF NOT EXISTS (
            SELECT * FROM sys.columns 
            WHERE Name = N'GeneratedFilesJson' AND Object_ID = Object_ID(N'WorkflowExecutions')
        )
        BEGIN
            ALTER TABLE WorkflowExecutions ADD GeneratedFilesJson NVARCHAR(MAX) NULL;
        END
        """
        cursor.execute(add_col_sql)

        cursor.close()
        conn.close()
        logger.info("MS SQL Server schema verified and upgraded successfully.")
        return True
    except Exception as exc:
        logger.warning(f"MS SQL Server initialization notice: {exc}")
        return False


def log_execution(
    session_id: str,
    prompt: str,
    status: str,
    iterations: int,
    files_count: int,
    review_feedback: Optional[str] = None,
    generated_files: Optional[Dict[str, str]] = None,
) -> bool:
    """Logs a completed or in-progress workflow execution with full code JSON to SQL Server."""
    settings = get_settings()
    if not settings.DB_ENABLED:
        return False

    try:
        conn = pyodbc.connect(settings.sql_connection_string, autocommit=True)
        cursor = conn.cursor()
        files_json_str = json.dumps(generated_files or {}, ensure_ascii=False) if generated_files else None

        insert_sql = """
        INSERT INTO WorkflowExecutions (SessionId, Prompt, Status, Iterations, GeneratedFilesCount, ReviewFeedback, GeneratedFilesJson)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        cursor.execute(
            insert_sql,
            (
                session_id,
                prompt[:4000],
                status,
                iterations,
                files_count,
                (review_feedback or "")[:4000],
                files_json_str,
            ),
        )
        cursor.close()
        conn.close()
        return True
    except Exception as exc:
        logger.debug(f"Failed to record execution log in database: {exc}")
        return False


def get_execution_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves chronological execution history from MS SQL Server."""
    settings = get_settings()
    if not settings.DB_ENABLED:
        return []

    try:
        conn = pyodbc.connect(settings.sql_connection_string)
        cursor = conn.cursor()
        query = f"""
        SELECT TOP (?) Id, SessionId, Prompt, Status, Iterations, GeneratedFilesCount, ReviewFeedback, CreatedAt
        FROM WorkflowExecutions
        ORDER BY Id DESC;
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r[0],
                "session_id": r[1],
                "prompt": r[2],
                "status": r[3],
                "iterations": r[4],
                "files_count": r[5],
                "review_feedback": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
            })
        cursor.close()
        conn.close()
        return results
    except Exception as exc:
        logger.warning(f"Error querying execution history: {exc}")
        return []


def get_execution_by_session_id(session_id: str) -> Optional[Dict[str, Any]]:
    """Fetches full execution session including saved code snapshot."""
    settings = get_settings()
    if not settings.DB_ENABLED:
        return None

    try:
        conn = pyodbc.connect(settings.sql_connection_string)
        cursor = conn.cursor()
        query = """
        SELECT TOP 1 Id, SessionId, Prompt, Status, Iterations, GeneratedFilesCount, ReviewFeedback, GeneratedFilesJson, CreatedAt
        FROM WorkflowExecutions
        WHERE SessionId = ?
        ORDER BY Id DESC;
        """
        cursor.execute(query, (session_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return None

        files_data = {}
        if row[7]:
            try:
                files_data = json.loads(row[7])
            except Exception:
                pass

        return {
            "id": row[0],
            "session_id": row[1],
            "prompt": row[2],
            "status": row[3],
            "iterations": row[4],
            "files_count": row[5],
            "review_feedback": row[6],
            "generated_code": files_data,
            "created_at": row[8].isoformat() if row[8] else None,
        }
    except Exception as exc:
        logger.warning(f"Error fetching execution for session {session_id}: {exc}")
        return None


def get_analytics_metrics() -> Dict[str, Any]:
    """Computes aggregated platform performance analytics from MS SQL Server."""
    settings = get_settings()
    if not settings.DB_ENABLED:
        return {"total_runs": 0, "pass_rate": 0, "avg_iterations": 0, "total_files": 0}

    try:
        conn = pyodbc.connect(settings.sql_connection_string)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), AVG(CAST(Iterations AS FLOAT)), SUM(GeneratedFilesCount) FROM WorkflowExecutions")
        row = cursor.fetchone()
        total_runs = row[0] or 0
        avg_iter = round(row[1] or 0.0, 1)
        total_files = row[2] or 0

        cursor.execute("SELECT COUNT(*) FROM WorkflowExecutions WHERE Status = 'completed'")
        completed_count = cursor.fetchone()[0] or 0
        pass_rate = round((completed_count / max(1, total_runs)) * 100, 1)

        cursor.close()
        conn.close()
        return {
            "total_runs": total_runs,
            "completed_runs": completed_count,
            "pass_rate_percentage": pass_rate,
            "average_iterations": avg_iter,
            "total_files_synthesized": total_files,
        }
    except Exception as exc:
        logger.warning(f"Error computing analytics metrics: {exc}")
        return {"total_runs": 0, "pass_rate": 0, "avg_iterations": 0, "total_files": 0}


def check_db_health() -> Dict[str, Any]:
    """Checks the health and reachability of MS SQL Server."""
    settings = get_settings()
    if not settings.DB_ENABLED:
        return {"status": "disabled", "details": "DB_ENABLED=false"}

    try:
        conn = pyodbc.connect(settings.sql_connection_string)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return {
            "status": "connected",
            "server": settings.DB_SERVER,
            "database": settings.DB_DATABASE,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "server": settings.DB_SERVER,
            "error": str(exc),
        }
