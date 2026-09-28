"""公共工具：数据库连接、执行 SQL 文件、查询成 DataFrame。

连接参数通过环境变量覆盖，默认连本机 MySQL 8，账号 analyst/analyst：
    MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB
"""
import os
from pathlib import Path

import pandas as pd
import pymysql
from pymysql.constants import CLIENT

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DIM_DIR = ROOT / "data" / "dim"
SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "outputs"
FIG_DIR = OUT_DIR / "figures"

DB = os.getenv("MYSQL_DB", "qc_dw")


def connect(db: str | None = DB) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "analyst"),
        password=os.getenv("MYSQL_PASSWORD", "analyst"),
        database=db,
        charset="utf8mb4",
        autocommit=True,
        local_infile=True,
        client_flag=CLIENT.MULTI_STATEMENTS,
    )


def run_sql_file(path: Path, db: str | None = DB) -> None:
    """整文件执行（支持多语句），逐个消费结果集，任何一句报错即抛出。"""
    sql = Path(path).read_text(encoding="utf-8")
    conn = connect(db)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
    finally:
        conn.close()
    print(f"[OK] {Path(path).relative_to(ROOT)}")


def query(sql: str, params=None) -> pd.DataFrame:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()
    return pd.DataFrame(rows, columns=cols)
