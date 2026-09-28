# 一键复现环境：Python 数据流程 + Spark（Hive 版 SQL）+ LibreOffice（Excel 透视表）+ Node（PPT / Word）
# 用法见 README「复现」：docker compose up --build
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# python3-uno 必须和系统 python3 配套：Excel 模板脚本用 /usr/bin/python3 调 LibreOffice
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-uno libreoffice-calc-nogui \
        default-jre-headless nodejs npm fonts-noto-cjk ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-hive.txt ./
RUN pip3 install --use-pep517 -r requirements.txt -r requirements-hive.txt pytest

COPY ppt/package.json ppt/package-lock.json ppt/
COPY report/package.json report/package-lock.json report/
RUN (cd ppt && npm ci) && (cd report && npm ci)

COPY . .
CMD ["bash", "scripts/docker_run.sh"]
