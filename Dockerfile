FROM python:3.11-slim

WORKDIR /app

# 安装服务器依赖 (无需 Playwright 浏览器，极度轻量级)
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    python-multipart \
    pydantic \
    email-validator \
    beautifulsoup4 \
    click \
    vcrpy \
    python-dotenv \
    filelock \
    gpsoauth \
    pycryptodomex \
    rich \
    requests \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

# 将服务端代码拷贝进容器
COPY gateway_server /app/gateway_server

# 容器数据卷挂载点 (用于 SQLite 数据库和凭据缓存存放)
VOLUME /app/data

# 暴露非标准端口
EXPOSE 18388

# 启动 uvicorn
CMD ["uvicorn", "gateway_server.main:app", "--host", "0.0.0.0", "--port", "18388"]
