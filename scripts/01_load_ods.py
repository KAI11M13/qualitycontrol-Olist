"""Step 1：建 ODS 表并把原始 CSV 灌入 MySQL（贴源，不做业务加工）。

入库后做一次行数对账：源文件行数 == 表行数，不一致直接报错。
"""
import numpy as np
import pandas as pd

from common import DIM_DIR, RAW_DIR, SQL_DIR, connect, run_sql_file

TABLES = {
    "ods_orders": "olist_orders_dataset.csv.gz",
    "ods_order_items": "olist_order_items_dataset.csv.gz",
    "ods_order_reviews": "olist_order_reviews_dataset.csv.gz",
    "ods_order_payments": "olist_order_payments_dataset.csv.gz",
    "ods_products": "olist_products_dataset.csv.gz",
    "ods_sellers": "olist_sellers_dataset.csv.gz",
    "ods_customers": "olist_customers_dataset.csv.gz",
    "ods_category_translation": "product_category_name_translation.csv.gz",
}
# 邮编前缀是字符串（有前导 0），不能按数字读
STR_COLS = {"seller_zip_code_prefix": str, "customer_zip_code_prefix": str}


def insert_df(conn, table: str, df: pd.DataFrame, batch: int = 5000) -> None:
    df = df.astype(object).where(pd.notna(df), None)
    cols = ", ".join(df.columns)
    ph = ", ".join(["%s"] * len(df.columns))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({ph})"
    rows = [tuple(r) for r in df.itertuples(index=False, name=None)]
    with conn.cursor() as cur:
        for i in range(0, len(rows), batch):
            cur.executemany(sql, rows[i : i + batch])


def main() -> None:
    run_sql_file(SQL_DIR / "01_ods_ddl.sql", db=None)
    conn = connect()
    try:
        for table, fname in TABLES.items():
            df = pd.read_csv(RAW_DIR / fname, dtype=STR_COLS)
            insert_df(conn, table, df)
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                n = cur.fetchone()[0]
            assert n == len(df), f"{table} 行数不一致: 源 {len(df)} vs 表 {n}"
            print(f"  {table:<28} {n:>8,} 行  (源文件 {len(df):,} 行, 对账通过)")

        # 维表：品类中文名 + 一级类目（人工整理，映射唯品会类目口径）
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS dim_category")
            cur.execute(
                """CREATE TABLE dim_category (
                    product_category_name VARCHAR(64) PRIMARY KEY,
                    category_en VARCHAR(64), category_cn VARCHAR(32), category_l1 VARCHAR(16)
                ) COMMENT 'DIM-品类维表（葡/英/中 + 一级类目）'"""
            )
        dim = pd.read_csv(DIM_DIR / "dim_category_cn.csv")
        insert_df(conn, "dim_category", dim)
        print(f"  {'dim_category':<28} {len(dim):>8,} 行")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
