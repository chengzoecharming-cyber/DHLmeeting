#!/usr/bin/env python3
"""用 Selenium 将 folium 生成的 HTML 渲染为高清 PNG。

运行：
    source venv/bin/activate
    python render_html_to_png.py

输出：
    coverage_heatmap.png
"""
from __future__ import annotations

import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def render_html_to_png(
    html_path: Path = Path("coverage_heatmap.html"),
    output: Path = Path("coverage_heatmap.png"),
    width: int = 1920,
    height: int = 1080,
    device_scale_factor: int = 2,
) -> None:
    html_path = html_path.resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"HTML 文件不存在: {html_path}")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--force-device-scale-factor=1")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(width, height)

    try:
        driver.get(f"file://{html_path}")
        # 等待地图瓦片加载（leaflet 容器存在且瓦片加载完成）
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.leaflet-tile-loaded"))
        )
        # 多等一会，确保所有瓦片和高热度图渲染完成
        time.sleep(3)

        # 执行 JS 设置 devicePixelRatio 并截图
        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": device_scale_factor,
                "mobile": False,
            },
        )
        time.sleep(2)

        driver.find_element(By.CSS_SELECTOR, "body").screenshot(str(output))
        print(f"已保存: {output.resolve()} ({width * device_scale_factor}x{height * device_scale_factor})")
    finally:
        driver.quit()


if __name__ == "__main__":
    render_html_to_png()
