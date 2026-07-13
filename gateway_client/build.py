import os
import sys
import subprocess
from pathlib import Path

def build_app():
    print("开始打包 NotebookLM Gateway 凭证助手...")
    
    # 确保当前目录是项目根目录
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    
    # 检查是否安装了 PyInstaller 和 PySide6
    try:
        import PyInstaller
        import PySide6
    except ImportError:
        print("错误：打包前请先安装依赖包！请执行：")
        print("pip install -e '.[client]' pyinstaller")
        sys.exit(1)

    # 构造 PyInstaller 命令行
    cmd = [
        "pyinstaller",
        "--clean",
        "-y",
        "-F",                    # 单文件打包
        "-w",                    # 无控制台黑框 (GUI 模式)
        "--name=notebooklm-gateway-client",
        # 收集 Playwright 相关的运行时文件
        "--collect-all=playwright",
        "--collect-all=notebooklm",
        "gateway_client/app.py"
    ]
    
    print(f"执行打包命令: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("\n🎉 打包完成！")
        print("打包生成的独立可执行文件位于：")
        if sys.platform == "win32":
            print(f"👉 {project_root / 'dist' / 'notebooklm-gateway-client.exe'}")
        else:
            print(f"👉 {project_root / 'dist' / 'notebooklm-gateway-client'}")
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败，错误码: {e.returncode}")

if __name__ == "__main__":
    build_app()
