import os
import sys
import json
import asyncio
import httpx
import traceback
from pathlib import Path

# 将项目根目录加入 sys.path 以防导入错误
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 桌面端程序本地工作目录
CLIENT_DIR = Path(__file__).resolve().parent


from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

# 导入底层的主令牌登录和同步逻辑
from gateway_server.notebooklm.cli.services.login import master_token as mt_service
from gateway_server.notebooklm.auth import generate_android_id

class LoginWorker(QThread):
    """用于在后台运行 Playwright 捕获主令牌和铸造 Cookie 的线程，防止 UI 假死"""
    log_signal = Signal(str)
    success_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, email, browser_type="chrome"):
        super().__init__()
        self.email = email
        self.browser_type = browser_type

    def run(self):
        try:
            self.log_signal.emit("🚀 [1/3] 正在拉起 Google 登录浏览器窗口，请在弹出的浏览器中完成登录...")
            
            # 1. 拦截 oauth_token (Master Token 阶段 1)
            token = mt_service.capture_oauth_token(browser=self.browser_type)
            if not token:
                self.error_signal.emit("❌ 未捕获到主令牌，请确保登录成功并进入了 NotebookLM 页面。")
                return

            self.log_signal.emit("✅ 成功捕获主令牌 (Master Token)。")
            self.log_signal.emit("🚀 [2/3] 正在向 Google 铸造 API Session Cookies 并生成关联配置...")

            # 2. 模拟本地路径，用于 bootstrap 生成临时凭证
            temp_profile_dir = CLIENT_DIR / "temp_profile"
            temp_profile_dir.mkdir(exist_ok=True)
            storage_path = temp_profile_dir / "storage_state.json"
            master_token_path = temp_profile_dir / "master_token.json"

            if master_token_path.exists():
                os.remove(master_token_path)
            if storage_path.exists():
                os.remove(storage_path)

            android_id = generate_android_id()
            self.log_signal.emit(f"   - 自动生成安卓客户端 ID: {android_id}")

            # 3. 运行同步异步机制生成 credentials 
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.log_signal.emit("   - 正在调用 Google API 并保存 credentials，这可能需要数秒...")
            loop.run_until_complete(
                mt_service.bootstrap(
                    email=self.email,
                    oauth_token=token,
                    android_id=android_id,
                    storage_path=storage_path,
                    master_token_path=master_token_path,
                    force=True
                )
            )

            # 读取生成的数据
            if not storage_path.exists() or not master_token_path.exists():
                self.error_signal.emit("❌ 铸造 Cookie 失败，凭证文件未能成功生成到本地。")
                return

            with open(storage_path, "r", encoding="utf-8") as f:
                storage_state = f.read()
            with open(master_token_path, "r", encoding="utf-8") as f:
                master_token_obj = json.load(f)
                master_token = master_token_obj.get("token")

            self.log_signal.emit("🚀 [3/3] 正在清理本地临时运行环境缓存...")
            # 清理临时文件
            os.remove(storage_path)
            os.remove(master_token_path)
            try:
                temp_profile_dir.rmdir()
            except Exception:
                pass

            self.success_signal.emit({
                "master_token": master_token,
                "storage_state": storage_state
            })

        except Exception as e:
            detailed_tb = traceback.format_exc()
            self.error_signal.emit(f"❌ 登录抓取过程发生异常: {e}\n\n详细崩溃日志:\n{detailed_tb}")



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NotebookLM Gateway 凭证助手")
        self.resize(550, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0e111a;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 13px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: #1a1f2e;
                border: 1px solid #2d3748;
                border-radius: 6px;
                padding: 6px 10px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #5865f2;
            }
            QPushButton {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4752c4;
            }
            QPushButton:disabled {
                background-color: #4d5660;
                color: #8e9297;
            }
            QTextEdit {
                background-color: #111420;
                border: 1px solid #2d3748;
                border-radius: 6px;
                color: #38bdf8;
                font-family: 'Courier New', Courier, monospace;
                font-size: 12px;
            }
        """)
        self.setup_ui()
        self.captured_credentials = None

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # 头部标题
        title_label = QLabel("NotebookLM Gateway 本地同步助手")
        title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title_label)

        # 参数配置区域
        config_layout = QVBoxLayout()
        config_layout.setSpacing(8)

        # 网关 API 地址
        lbl_url = QLabel("远程网关 API 地址 (HTTPS 域名):")
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("例如: https://note.aisenno.com")
        config_layout.addWidget(lbl_url)
        config_layout.addWidget(self.txt_url)

        # 网关管理员 Token
        lbl_admin_token = QLabel("网关管理员 Token (NOTEBOOKLM_ADMIN_TOKEN):")
        self.txt_admin_token = QLineEdit()
        self.txt_admin_token.setEchoMode(QLineEdit.Password)
        self.txt_admin_token.setPlaceholderText("请输入服务器部署时配置的管理密码")
        config_layout.addWidget(lbl_admin_token)
        config_layout.addWidget(self.txt_admin_token)

        # 托管邮箱
        lbl_email = QLabel("当前 Google 账号邮箱:")
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("例如: guyue7737@gmail.com")
        config_layout.addWidget(lbl_email)
        config_layout.addWidget(self.txt_email)

        # 此账号自定义的 api_key
        lbl_api_key = QLabel("为该账号分配的外部调用 API Key (自定义):")
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("例如: my_notebook_key_abc123")
        config_layout.addWidget(lbl_api_key)
        config_layout.addWidget(self.txt_api_key)

        layout.addLayout(config_layout)

        # 操作按钮区
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("🔑 登录 Google 获取凭据")
        self.btn_login.clicked.connect(self.start_google_login)
        self.btn_upload = QPushButton("🚀 一键同步到服务器")
        self.btn_upload.setEnabled(False)
        self.btn_upload.clicked.connect(self.upload_to_server)
        self.btn_test = QPushButton("🔍 联通性测试")
        self.btn_test.setEnabled(False)
        self.btn_test.clicked.connect(self.test_connection)
        
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_upload)
        btn_layout.addWidget(self.btn_test)
        layout.addLayout(btn_layout)

        # 日志输出区
        lbl_log = QLabel("操作日志输出区:")
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        layout.addWidget(lbl_log)
        layout.addWidget(self.txt_log)

        # 默认回填本地缓存
        self.load_settings()

    def log(self, message):
        self.txt_log.append(message)

    def load_settings(self):
        """加载上次填写的参数"""
        try:
            settings_file = CLIENT_DIR / "settings.json"
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.txt_url.setText(settings.get("url", ""))
                    self.txt_admin_token.setText(settings.get("admin_token", ""))
                    self.txt_email.setText(settings.get("email", ""))
                    self.txt_api_key.setText(settings.get("api_key", ""))
        except Exception:
            pass

    def save_settings(self):
        """保存当前填写的参数"""
        try:
            settings = {
                "url": self.txt_url.text().strip(),
                "admin_token": self.txt_admin_token.text().strip(),
                "email": self.txt_email.text().strip(),
                "api_key": self.txt_api_key.text().strip()
            }
            settings_file = CLIENT_DIR / "settings.json"
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f)
        except Exception:
            pass

    def start_google_login(self):
        email = self.txt_email.text().strip()
        if not email:
            QMessageBox.warning(self, "警告", "请先填入当前 Google 账号邮箱！")
            return

        self.save_settings()
        self.btn_login.setEnabled(False)
        self.captured_credentials = None
        self.btn_upload.setEnabled(False)
        self.btn_test.setEnabled(False)

        # 启动后台线程登录
        # 默认尝试使用 chrome 驱动，如果系统里没有会自动回退到 chromium
        self.worker = LoginWorker(email, browser_type="chrome")
        self.worker.log_signal.connect(self.log)
        self.worker.success_signal.connect(self.on_login_success)
        self.worker.error_signal.connect(self.on_login_error)
        self.worker.start()

    def on_login_success(self, creds):
        self.captured_credentials = creds
        self.log("✅ 凭证抓取并铸造成功！已在内存中暂存。")
        self.btn_login.setEnabled(True)
        self.btn_upload.setEnabled(True)

    def on_login_error(self, err_msg):
        self.log(f"❌ 错误: {err_msg}")
        self.btn_login.setEnabled(True)
        QMessageBox.critical(self, "错误", err_msg)

    def upload_to_server(self):
        url = self.txt_url.text().strip().rstrip("/")
        admin_token = self.txt_admin_token.text().strip()
        email = self.txt_email.text().strip()
        api_key = self.txt_api_key.text().strip()

        if not url or not admin_token or not api_key:
            QMessageBox.warning(self, "警告", "请填满网关地址、管理员 Token 以及自定义 API Key！")
            return

        if not self.captured_credentials:
            QMessageBox.warning(self, "警告", "请先登录 Google 获取凭据！")
            return

        self.log(f"正在将凭证推送至网关 {url}/v1/auth/credentials ...")
        
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "api_key": api_key,
            "master_token": self.captured_credentials["master_token"],
            "storage_state": self.captured_credentials["storage_state"]
        }

        try:
            resp = httpx.post(f"{url}/v1/auth/credentials", json=payload, headers=headers, timeout=15.0)
            if resp.status_code == 200:
                self.log("✅ 凭证同步成功！服务器已经完成热重载。")
                self.btn_test.setEnabled(True)
                QMessageBox.information(self, "成功", "凭证已成功同步至服务器并实时生效！")
                self.save_settings()
            else:
                self.log(f"❌ 上传失败，服务器返回状态码: {resp.status_code}, 内容: {resp.text}")
                QMessageBox.critical(self, "错误", f"同步失败！状态码: {resp.status_code}\n{resp.text}")
        except Exception as e:
            self.log(f"❌ 网络请求异常: {e}")
            QMessageBox.critical(self, "异常", f"连接服务器发生异常: {e}")

    def test_connection(self):
        url = self.txt_url.text().strip().rstrip("/")
        api_key = self.txt_api_key.text().strip()

        self.log(f"正在使用当前 API Key 发起联通性测试 (GET {url}/v1/notebooks)...")
        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        try:
            resp = httpx.get(f"{url}/v1/notebooks", headers=headers, timeout=10.0)
            if resp.status_code == 200:
                self.log(f"✅ 联通性测试成功！响应内容: {resp.json()}")
                QMessageBox.information(self, "测试成功", "接口调用联调成功！")
            else:
                self.log(f"❌ 测试失败，服务器返回: {resp.status_code}, 内容: {resp.text}")
                QMessageBox.critical(self, "测试失败", f"接口测试失败！状态码: {resp.status_code}\n{resp.text}")
        except Exception as e:
            self.log(f"❌ 测试异常: {e}")
            QMessageBox.critical(self, "异常", f"测试请求发生异常: {e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
