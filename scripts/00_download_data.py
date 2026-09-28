"""Step 0：下载原始数据（仓库里已自带 data/raw/*.csv.gz，通常不需要再跑）。

数据：Olist Brazilian E-Commerce Public Dataset（Kaggle: olistbr/brazilian-ecommerce，CC BY-NC-SA 4.0）
Kaggle 需要登录，这里从 GitHub 上的 gzip 镜像下载，下载后校验行数与官方一致。
"""
import urllib.request

import pandas as pd

from common import RAW_DIR

MIRROR = "https://raw.githubusercontent.com/ckoliveiraa/pipeline-olist/main/raw/{}.csv.gz"
EXPECTED = {   # 官方数据集行数
    "olist_orders_dataset": 99441,
    "olist_order_items_dataset": 112650,
    "olist_order_reviews_dataset": 99224,
    "olist_order_payments_dataset": 103886,
    "olist_products_dataset": 32951,
    "olist_sellers_dataset": 3095,
    "olist_customers_dataset": 99441,
    "product_category_name_translation": 71,
}

if __name__ == "__main__":
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, n in EXPECTED.items():
        dst = RAW_DIR / f"{name}.csv.gz"
        if not dst.exists():
            urllib.request.urlretrieve(MIRROR.format(name), dst)
        rows = len(pd.read_csv(dst))
        assert rows == n, f"{name}: {rows} 行，官方为 {n} 行"
        print(f"  {name:<40} {rows:>8,} 行 ✓")
