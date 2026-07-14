import os
import sys
import subprocess
from pathlib import Path

def prepare_icons():
    # 从 logo.png 生成 logo.ico
    client_dir = Path(__file__).resolve().parent
    png_path = client_dir / "logo.png"
    ico_path = client_dir / "logo.ico"
    
    if not png_path.exists():
        print("未找到 logo.png，跳过图标生成")
        return None
        
    try:
        from PIL import Image
        print("正在将 logo.png 转换为 logo.ico...")
        img = Image.open(png_path)
        # 常见 ICO 尺寸
        img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(f"成功生成 ICO 图标: {ico_path}")
        return ico_path
    except Exception as e:
        print(f"提示：使用 Pillow 转换 ICO 图标失败 ({e})，将无法应用 Windows 外壳图标。您可以先执行 pip install pillow 来自动生成。")
        return None

def build_app():
    print("开始打包 NotebookLM Gateway 凭证助手...")
    
    # 确保当前目录是项目根目录
    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    
    # 准备图标
    ico_path = prepare_icons()

    # 检查是否安装了 PyInstaller 和 PySide6
    try:
        import PyInstaller
        import PySide6
    except ImportError:
        print("错误：打包前请先安装依赖包！请执行：")
        print("pip install PyInstaller PySide6 httpx playwright pillow")
        sys.exit(1)

    # 动态定位当前虚拟环境下的 pyinstaller 可执行文件路径
    python_dir = Path(sys.executable).parent
    pyinstaller_bin = "pyinstaller.exe" if sys.platform == "win32" else "pyinstaller"
    pyinstaller_path = python_dir / pyinstaller_bin
    if not pyinstaller_path.exists():
        pyinstaller_path = Path(pyinstaller_bin)

    # 构造 PyInstaller 命令行
    cmd = [
        str(pyinstaller_path),
        "--clean",
        "-y",
        "-F",                    # 单文件打包
        "-w",                    # 无控制台黑框 (GUI 模式)
        "--name=notebooklm-gateway-client",
        # 极其重要：把 gateway_server 目录整体打包进数据，供客户端加载底层代码
        f"--add-data=gateway_server{os.pathsep}gateway_server",
        # 把客户端的 logo.png 也打包进可执行文件以供窗口加载展示
        f"--add-data=gateway_client/logo.png{os.pathsep}gateway_client",
        # 收集 Playwright 相关的运行时文件
        "--collect-all=playwright",
        # 拷贝 gpsoauth 和 notebooklm-py 的元数据，防止 importlib.metadata 报错
        "--copy-metadata=gpsoauth",
        "--copy-metadata=notebooklm-py",
    ]
    
    # 如果成功生成了 .ico 图标，或者在 macOS 下有合适图标，添加 --icon 属性
    if ico_path and ico_path.exists():
        cmd.append(f"--icon={ico_path}")
    elif sys.platform == "darwin":
        # macOS 下直接尝试传递 png，PyInstaller 在很多版本上可以自动将其编译为 icns
        png_path = Path(__file__).resolve().parent / "logo.png"
        if png_path.exists():
            cmd.append(f"--icon={png_path}")
            
    cmd.append("gateway_client/app.py")
    
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
