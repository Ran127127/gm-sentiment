FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（lxml编译需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libxml2-dev libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render通过PORT环境变量指定端口，本地默认8000
ENV PORT=8000

EXPOSE ${PORT}

RUN chmod +x start.sh
CMD ["./start.sh"]
