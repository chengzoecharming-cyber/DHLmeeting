#!/usr/bin/env python3
"""
Export HTML Keynote slides to PDF.

Usage:
    python3 export_pdf.py

Requires:
    - Google Chrome installed at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
    - Python 3
    - Pillow (auto-installed in temporary venv if not present)
"""

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ============== 配置 ==============
HTML_FILE = "jiaheng-logistics-bid-keynote.html"
OUTPUT_PDF = "嘉亨物流运输解决方案-投标版.pdf"
PORT = 8765
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SLIDE_WIDTH = 1280
SLIDE_HEIGHT = 720
SCALE_FACTOR = 2  # 2x 高清截图
# ==================================


def get_slide_count(html_path: str) -> int:
    """Count <section class="slide" ...> elements."""
    text = Path(html_path).read_text(encoding="utf-8")
    return len(re.findall(r'<section\s+class="slide[^"]*"', text))


def check_chrome():
    if not Path(CHROME_PATH).exists():
        print(f"错误：找不到 Chrome，路径应为 {CHROME_PATH}")
        sys.exit(1)


def start_server(work_dir: str, port: int) -> subprocess.Popen:
    """Start a simple HTTP server in the background."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=work_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to be ready
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/{HTML_FILE}", timeout=1)
            return proc
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError("HTTP server failed to start")


def capture_slide(url: str, output_png: str):
    """Use Chrome headless to screenshot a single slide."""
    cmd = [
        CHROME_PATH,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        f"--force-device-scale-factor={SCALE_FACTOR}",
        f"--window-size={SLIDE_WIDTH},{SLIDE_HEIGHT}",
        f"--screenshot={output_png}",
        url,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ensure_pillow():
    """Ensure Pillow is available; install to temporary venv if needed."""
    try:
        from PIL import Image
        return Image
    except ImportError:
        print("Pillow 未安装，正在创建临时虚拟环境并安装...")
        venv_dir = Path(".export_pdf_venv")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        pip = venv_dir / "bin" / "pip"
        subprocess.run([str(pip), "install", "-q", "Pillow"], check=True)

        # Run this script again inside the venv
        python = venv_dir / "bin" / "python"
        subprocess.run([str(python), __file__] + sys.argv[1:])
        sys.exit(0)


def combine_images_to_pdf(png_paths: list[str], output_path: str):
    from PIL import Image

    images = []
    for path in png_paths:
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        images.append(img)

    images[0].save(
        output_path,
        "PDF",
        resolution=96 * SCALE_FACTOR,
        save_all=True,
        append_images=images[1:],
    )


def main():
    work_dir = Path(__file__).parent.resolve()
    html_path = work_dir / HTML_FILE
    output_pdf = work_dir / OUTPUT_PDF

    if not html_path.exists():
        print(f"错误：找不到 {HTML_FILE}")
        sys.exit(1)

    check_chrome()
    slide_count = get_slide_count(str(html_path))
    print(f"检测到 {slide_count} 张幻灯片，开始导出...")

    # Ensure Pillow is available
    ensure_pillow()

    server_proc = None
    temp_dir = tempfile.mkdtemp(prefix="slides_")

    try:
        print(f"启动本地服务器: http://127.0.0.1:{PORT}")
        server_proc = start_server(str(work_dir), PORT)

        png_paths = []
        for i in range(1, slide_count + 1):
            png_path = os.path.join(temp_dir, f"slide_{i:02d}.png")
            url = f"http://127.0.0.1:{PORT}/{HTML_FILE}?export=1#{i}"
            print(f"  截图第 {i}/{slide_count} 页...")
            capture_slide(url, png_path)
            png_paths.append(png_path)

        print(f"合并为 PDF: {output_pdf.name}")
        combine_images_to_pdf(png_paths, str(output_pdf))

        size_kb = output_pdf.stat().st_size / 1024
        print(f"完成！{slide_count} 页，{size_kb:.1f} KB")
        print(f"文件路径: {output_pdf}")

    finally:
        if server_proc:
            server_proc.terminate()
            server_proc.wait()
        for path in png_paths:
            try:
                os.remove(path)
            except OSError:
                pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass


if __name__ == "__main__":
    main()
