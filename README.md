# NotebookLM Gateway 🚀

一个独立、自包含、支持**多租户/多账号动态路由**的 Google NotebookLM 外部 API 网关服务。

配有跨平台的桌面助手客户端，实现 Google 一键登录、自动获取主令牌（Master Token）并安全推送到服务器，全程无需配置任何复杂的凭证文件，开箱即用。

---

## 🌟 核心特性

*   **极简部署**：一键 `docker-compose up` 启动，无需手动在容器中安装 Chrome 浏览器（登录环节全部转移到本地桌面端进行，服务器端保持极度轻量）。
*   **多账号多 Key 路由**：支持托管多个 Google 账号，为每个账号分配独立的 `api_key` 进行分权调用。
*   **热更新**：通过本地助手同步凭证后，服务端自动热加载会话，无需重启容器。
*   **自带控制台**：内置高颜值极简 Web 控制台，轻松管理托管账号、复制及修改 API Key。
*   **Cookie 自动续期**：基于 Master Token 持久主令牌机制，容器在后台自动刷新 Cookie，持久稳定运行。

---

## 📦 1. 服务端部署与更新指南 (Ubuntu / 1Panel)

### 第一步：获取代码并一键启动
在服务器终端中执行：

```bash
# 克隆代码
git clone https://github.com/HuFakai/notebooklm-gateway.git
cd notebooklm-gateway

# 1. 复制配置文件并修改参数
cp .env.example .env

# 编辑 .env 文件，修改你的 GATEWAY_PORT 和 GATEWAY_ADMIN_TOKEN 管理密码
nano .env

# 2. 启动 Docker 容器
docker compose up -d
```

> [!IMPORTANT]
> - 容器会默认自动加载项目根目录下的 `.env` 文件。
> - `GATEWAY_PORT`：代表要映射到宿主机上的访问端口（默认使用 `18388`）。
> - `GATEWAY_ADMIN_TOKEN`：管理员管理令牌，用于上传凭证和控制台身份登录验证。强烈建议将其修改为一个高强度的随机 Token，且该变量保存在本地 `.env` 中，已被 Git 自动忽略，以保安全。

### 第二步：配置反向代理与 HTTPS
由于 API 调用及凭证上传包含敏感密钥，强烈建议在 1Panel 中将域名（如 `note.aisenno.com`）反向代理至 **`http://notebooklm-gateway-server:18388`**（容器局域网直连），并在网站设置中申请一键 SSL 证书以启用 HTTPS 加密。

部署完成后，你可以在浏览器直接访问网关控制台：
`https://你的域名/admin`

第一次进入控制台需要输入在 `.env` 中设置的 **`GATEWAY_ADMIN_TOKEN`** 管理密码进行安全登录，登录成功后方可查看和管理各个托管账号的凭证和 Key。

### 第三步：服务端版本平滑更新
当本网关项目发布了新版本（或您更新了 GitHub 仓库源码），可以通过以下几步在服务器上一键平滑更新部署：

```bash
# 1. 进入网关目录
cd notebooklm-gateway

# 2. 停止并删除旧容器
docker compose down

# 3. 拉取最新代码 (会保留您的本地 .env 配置文件)
git pull origin main

# 4. 重新构建 Docker 镜像并后台启动运行
docker compose up -d --build
```

---

## 🖥️ 2. 本地助手客户端使用指南 (Mac & Win)

本地助手 `notebooklm-gateway-client` 负责协助你在本地安全登录 Google，提取凭证并同步至远端服务器。

### 如何运行客户端
```bash
# 1. 如果本地尚未创建 Python 虚拟环境，请先创建：
python -m venv .venv

# 2. 激活项目本地的虚拟环境
# macOS / Linux:
source .venv/bin/activate
# Windows (cmd):
# .venv\Scripts\activate.bat
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# 3. 安装客户端所必须的依赖项与浏览器驱动
pip install PySide6 playwright httpx pyinstaller
playwright install chrome

# 4. 启动本地助手
python gateway_client/app.py
```

### 编译打包为独立软件
在将本地助手编译打包为独立软件前，**请确保您已执行上述“如何运行客户端”中的第一步，在本地 Python 虚拟环境中成功安装了所有依赖项**。

在您的电脑终端直接执行打包脚本，打包完成后会在 `dist/` 目录下生成可以直接双击运行的桌面软件：
```bash
python gateway_client/build.py
```

### 使用步骤：
1. 打开助手，输入你的【远程网关 API 地址】和【管理员 Token】。
2. 输入你的当前 Google 账号邮箱，并自定义本账号调用 API 的 `api_key`。
3. 点击 **【🔑 登录 Google 获取凭据】**，在弹出的窗口中登录 Google 账号。
4. 登录完成并跳转至 NotebookLM 页面后，系统会自动拦截凭证。
5. 点击 **【🚀 一键同步到服务器】**，凭证即刻同步到你的云端数据库并实时生效。
6. 点击 **【🔍 联通性测试】**，即可验证网关是否打通！

---

## 🔑 3. 外部 API 调用说明

网关完全兼容 `notebooklm-py` 的所有路由规格。你只需要把 Header 修改为：
`Authorization: Bearer <你为该账号分配的 api_key>`

### 示例 1：获取对应账号 of 笔记本列表 (Curl)
```bash
curl -X GET "https://note.aisenno.com/v1/notebooks" \
     -H "Authorization: Bearer my_custom_api_key_123"
```

### 示例 2：使用 Python 客户端与特定账号进行对话
```python
import httpx

url = "https://note.aisenno.com/v1/notebooks/YOUR_NOTEBOOK_ID/chat"
headers = {
    "Authorization": "Bearer my_custom_api_key_123", # 对应账号的 key
    "Content-Type": "application/json"
}
payload = {
    "input": "请帮我总结一下这本笔记本的核心内容"
}

with httpx.Client() as client:
    response = client.post(url, json=payload, headers=headers, timeout=60.0)
    print(response.json())
```

---

## 💖 鸣谢与参考

本项目在开发过程中，深受以下开源项目的启发与核心能力支持，在此表示诚挚的感谢：

1.  **[teng-lin / notebooklm-py](https://github.com/teng-lin/notebooklm-py)**：提供了 Google NotebookLM 底层协议和凭据加载的核心提取引擎。
2.  **[gnh1201 / notebooklm-rest-api](https://github.com/gnh1201/notebooklm-rest-api)**：提供了轻量化部署与多账号 API 集中网关的架构设计灵感。

---

## 📄 开源协议

本项目基于 **MIT License** 协议开源。您可以自由地使用、修改和分发本项目代码，但请保留原作者的版权声明及开源协议。
