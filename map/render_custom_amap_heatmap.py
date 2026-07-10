#!/usr/bin/env python3
"""生成可直接 Selenium 截图的高德风格热力图 HTML，并渲染为 PNG。

运行：
    source venv/bin/activate
    python render_custom_amap_heatmap.py

输出：
    coverage_heatmap.png  (1920 x 1080，可缩放为 2x 高清)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ---------- 数据 ----------
DATA = [
    # 广东（高权重，核心红色区域）
    (23.1291, 113.2644, 1.00),
    (22.5431, 114.0579, 0.98),
    (22.5112, 113.3927, 0.90),
    (23.0207, 113.7518, 0.90),
    (22.2710, 113.5670, 0.85),
    (22.8700, 113.6800, 0.80),
    (23.5515, 116.3716, 0.80),
    (23.1580, 113.3300, 0.80),
    (22.7830, 113.0900, 0.75),
    (22.2900, 110.2900, 0.75),
    (21.2700, 110.3500, 0.75),
    (24.8120, 113.5900, 0.70),
    (23.3500, 116.7000, 0.70),
    (22.4200, 114.0500, 0.70),
    (23.0300, 113.7000, 0.68),
    (22.1900, 113.5400, 0.65),
    (22.6000, 114.9000, 0.65),
    (21.9500, 112.7000, 0.65),
    (22.3500, 111.9500, 0.60),
    (23.8000, 112.4500, 0.60),
    (23.3500, 116.2000, 0.60),
    (22.7800, 115.3800, 0.60),
    (23.0200, 112.4500, 0.55),
    (24.3000, 116.1200, 0.55),
    # 湖南
    (28.2280, 112.9388, 0.85),
    (27.8278, 112.9730, 0.70),
    (26.8890, 112.5720, 0.70),
    (27.8468, 113.1280, 0.70),
    (29.0316, 111.6983, 0.65),
    (29.1520, 110.4780, 0.65),
    (28.5880, 112.3600, 0.60),
    (27.2330, 111.4670, 0.60),
    (25.8080, 113.2360, 0.60),
    (26.4200, 111.6000, 0.55),
    (27.7300, 109.1800, 0.55),
    (27.5750, 110.0200, 0.55),
    (27.7000, 111.4300, 0.50),
    (28.6000, 109.9600, 0.50),
    # 湖北
    (30.5928, 114.3055, 0.85),
    (30.3000, 112.2800, 0.70),
    (30.6800, 111.2800, 0.70),
    (30.3300, 114.3200, 0.70),
    (30.2000, 115.0800, 0.65),
    (31.7100, 112.2500, 0.65),
    (32.3900, 111.6700, 0.65),
    (30.9300, 113.4000, 0.60),
    (32.1300, 114.0800, 0.60),
    (30.4200, 114.9300, 0.60),
    (30.4500, 112.2000, 0.55),
    (31.3500, 113.7500, 0.55),
    (29.6500, 111.6800, 0.55),
    (31.7300, 114.3800, 0.50),
    (29.8500, 114.3200, 0.50),
    (30.6800, 110.9700, 0.50),
    # 海南
    (20.0440, 110.1999, 0.80),
    (18.2520, 109.5120, 0.75),
    (19.2400, 110.4700, 0.65),
    (19.5200, 109.5800, 0.60),
    (18.8000, 110.4000, 0.60),
    (19.7000, 110.3300, 0.55),
    (18.6000, 108.9000, 0.55),
    (18.9800, 109.4200, 0.50),
    # 补充散点（仅用于过渡，权重较低避免过度扩散）
    (22.5000, 111.5000, 0.15),
    (24.5000, 113.5000, 0.15),
    (26.5000, 112.5000, 0.15),
    (29.5000, 113.5000, 0.15),
    (28.5000, 110.5000, 0.15),
    (30.0000, 110.5000, 0.15),
    (20.5000, 111.0000, 0.15),
    (19.5000, 109.5000, 0.15),
    (21.8000, 110.5000, 0.12),
    (23.8000, 115.0000, 0.12),
    (27.0000, 113.5000, 0.12),
    (29.8000, 112.5000, 0.12),
    (20.0000, 110.5000, 0.12),
]

CAPITALS = [
    ("广州", 23.1291, 113.2644),
    ("长沙", 28.2280, 112.9388),
    ("武汉", 30.5928, 114.3055),
    ("海口", 20.0440, 110.1999),
]

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>coverage_heatmap</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css" />
<style>
  html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #f2f3f4;
  }}
  #map {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }}
  .leaflet-control-attribution {{
    font-size: 10px !important;
    padding: 2px 6px !important;
    background: rgba(255,255,255,0.6) !important;
  }}
  .city-label {{
    font-size: 14px;
    font-weight: bold;
    color: #2a2a2a;
    text-shadow:
      1px 1px 0 #fff,
      -1px -1px 0 #fff,
      1px -1px 0 #fff,
      -1px 1px 0 #fff,
      0 0 4px #fff;
    white-space: nowrap;
    transform: translateX(-50%) translateY(-150%);
  }}
  .city-dot {{
    width: 10px;
    height: 10px;
    background: #ff3b30;
    border: 2px solid #333;
    border-radius: 50%;
    transform: translate(-50%, -50%);
  }}
</style>
</head>
<body>
<div id="map"></div>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/gh/python-visualization/folium@main/folium/templates/leaflet_heat.min.js"></script>
<script>
  const map = L.map('map', {{
  zoomSnap: 0.25,
  zoomControl: false,
  attributionControl: false,
  preferCanvas: true
}});

// 聚焦广东、湖南、湖北、海南四省
map.fitBounds(
  [[18.0, 108.0], [33.5, 117.5]],
  {{ padding: [20, 20], animate: false }}
);

  L.tileLayer(
    'https://webrd0{{s}}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={{x}}&y={{y}}&z={{z}}',
    {{
      subdomains: ['1', '2', '3', '4'],
      maxZoom: 18,
      minZoom: 1,
      attribution: '高德地图'
    }}
  ).addTo(map);

  const heatData = {data_json};
  L.heatLayer(heatData, {{
    minOpacity: 0.35,
    maxZoom: 6,
    radius: 36,
    blur: 28,
    gradient: {{
      0.0: 'rgba(0,0,180,0.25)',
      0.2: 'rgba(0,120,220,0.55)',
      0.4: 'rgba(0,220,220,0.75)',
      0.6: 'rgba(60,220,60,0.85)',
      0.8: 'rgba(255,220,0,0.95)',
      1.0: 'rgba(255,40,0,1.0)'
    }}
  }}).addTo(map);

  const capitals = {capitals_json};
  capitals.forEach(([name, lat, lng]) => {{
    const icon = L.divIcon({{
      className: '',
      html: '<div class="city-dot"></div><div class="city-label">' + name + '</div>',
      iconSize: [0, 0]
    }});
    L.marker([lat, lng], {{ icon: icon }}).addTo(map);
  }});
</script>
</body>
</html>
"""


def generate_html(html_path: Path = Path("coverage_heatmap_render.html")) -> Path:
    data_json = json.dumps([[lat, lng, w] for lat, lng, w in DATA])
    capitals_json = json.dumps(CAPITALS)
    html = HTML_TEMPLATE.format(data_json=data_json, capitals_json=capitals_json)
    html_path.write_text(html, encoding="utf-8")
    print(f"已生成 HTML: {html_path.resolve()}")
    return html_path


def render_to_png(
    html_path: Path,
    output: Path = Path("coverage_heatmap.png"),
    width: int = 1920,
    height: int = 1080,
    scale: int = 2,
) -> None:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--force-device-scale-factor=1")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(width, height)

    try:
        driver.get(f"file://{html_path.resolve()}")
        # 等待至少一张瓦片加载
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img.leaflet-tile-loaded"))
        )
        # 额外等待，确保热力图层平滑过渡完成
        time.sleep(4)

        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": scale,
                "mobile": False,
            },
        )
        time.sleep(2)

        driver.find_element(By.CSS_SELECTOR, "#map").screenshot(str(output))
        print(f"已保存 PNG: {output.resolve()} ({width * scale}x{height * scale})")
    finally:
        driver.quit()


if __name__ == "__main__":
    html = generate_html()
    render_to_png(html)
