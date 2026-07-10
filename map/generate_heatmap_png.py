#!/usr/bin/env python3
"""渲染可直接放入 PPT 的业务覆盖热力图 PNG。

运行：
    source venv/bin/activate
    python generate_heatmap_png.py

输出：
    coverage_heatmap.png  (1920 x 1080，300 dpi，透明/浅色底图)
"""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from scipy.stats import gaussian_kde

# ---------- 业务数据：纬度, 经度, 权重 ----------
DATA = [
    # 广东（高权重，核心红色区域）
    (23.1291, 113.2644, 1.00),  # 广州
    (22.5431, 114.0579, 0.98),  # 深圳
    (22.5112, 113.3927, 0.90),  # 佛山
    (23.0207, 113.7518, 0.90),  # 东莞
    (22.2710, 113.5670, 0.85),  # 珠海
    (22.8700, 113.6800, 0.80),  # 中山
    (23.5515, 116.3716, 0.80),  # 潮州
    (23.1580, 113.3300, 0.80),  # 番禺/广州南
    (22.7830, 113.0900, 0.75),  # 江门
    (22.2900, 110.2900, 0.75),  # 茂名
    (21.2700, 110.3500, 0.75),  # 湛江
    (24.8120, 113.5900, 0.70),  # 韶关
    (23.3500, 116.7000, 0.70),  # 汕头
    (22.4200, 114.0500, 0.70),  # 深圳西/宝安
    (23.0300, 113.7000, 0.68),  # 东莞东
    (22.1900, 113.5400, 0.65),  # 横琴/澳门边
    (22.6000, 114.9000, 0.65),  # 惠州
    (21.9500, 112.7000, 0.65),  # 阳江
    (22.3500, 111.9500, 0.60),  # 云浮
    (23.8000, 112.4500, 0.60),  # 清远
    (23.3500, 116.2000, 0.60),  # 揭阳
    (22.7800, 115.3800, 0.60),  # 汕尾
    (23.0200, 112.4500, 0.55),  # 肇庆
    (24.3000, 116.1200, 0.55),  # 梅州

    # 湖南
    (28.2280, 112.9388, 0.85),  # 长沙
    (27.8278, 112.9730, 0.70),  # 湘潭
    (26.8890, 112.5720, 0.70),  # 衡阳
    (27.8468, 113.1280, 0.70),  # 株洲
    (29.0316, 111.6983, 0.65),  # 常德
    (29.1520, 110.4780, 0.65),  # 张家界
    (28.5880, 112.3600, 0.60),  # 益阳
    (27.2330, 111.4670, 0.60),  # 邵阳
    (25.8080, 113.2360, 0.60),  # 郴州
    (26.4200, 111.6000, 0.55),  # 永州
    (27.7300, 109.1800, 0.55),  # 湘西/吉首
    (27.5750, 110.0200, 0.55),  # 怀化
    (27.7000, 111.4300, 0.50),  # 娄底
    (28.6000, 109.9600, 0.50),  # 怀化北

    # 湖北
    (30.5928, 114.3055, 0.85),  # 武汉
    (30.3000, 112.2800, 0.70),  # 荆州
    (30.6800, 111.2800, 0.70),  # 宜昌
    (30.3300, 114.3200, 0.70),  # 鄂州
    (30.2000, 115.0800, 0.65),  # 黄石
    (31.7100, 112.2500, 0.65),  # 荆门
    (32.3900, 111.6700, 0.65),  # 襄阳
    (30.9300, 113.4000, 0.60),  # 孝感
    (32.1300, 114.0800, 0.60),  # 随州
    (30.4200, 114.9300, 0.60),  # 黄冈
    (30.4500, 112.2000, 0.55),  # 天门/仙桃
    (31.3500, 113.7500, 0.55),  # 应城/孝感北
    (29.6500, 111.6800, 0.55),  # 潜江
    (31.7300, 114.3800, 0.50),  # 大悟/红安
    (29.8500, 114.3200, 0.50),  # 咸宁
    (30.6800, 110.9700, 0.50),  # 枝江

    # 海南
    (20.0440, 110.1999, 0.80),  # 海口
    (18.2520, 109.5120, 0.75),  # 三亚
    (19.2400, 110.4700, 0.65),  # 琼海
    (19.5200, 109.5800, 0.60),  # 儋州/洋浦
    (18.8000, 110.4000, 0.60),  # 万宁
    (19.7000, 110.3300, 0.55),  # 文昌
    (18.6000, 108.9000, 0.55),  # 东方
    (18.9800, 109.4200, 0.50),  # 乐东

    # 补充散点（让区域过渡更自然）
    (22.5000, 111.5000, 0.30),
    (24.5000, 113.5000, 0.30),
    (26.5000, 112.5000, 0.30),
    (29.5000, 113.5000, 0.30),
    (28.5000, 110.5000, 0.30),
    (30.0000, 110.5000, 0.30),
    (20.5000, 111.0000, 0.30),
    (19.5000, 109.5000, 0.30),
    (21.8000, 110.5000, 0.25),
    (23.8000, 115.0000, 0.25),
    (27.0000, 113.5000, 0.25),
    (29.8000, 112.5000, 0.25),
    (20.0000, 110.5000, 0.25),
]

CAPITALS = [
    ("广州", 23.1291, 113.2644),
    ("长沙", 28.2280, 112.9388),
    ("武汉", 30.5928, 114.3055),
    ("海口", 20.0440, 110.1999),
]


# ---------- 高德公开标准地图瓦片（浅色） ----------
def fetch_amap_tile(x: int, y: int, z: int) -> np.ndarray | None:
    """获取高德标准地图瓦片（style=8 为浅色），失败返回 None。"""
    url = f"https://webrd0{(x + y) % 4 + 1}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        return np.array(img)
    except Exception:
        return None


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    """经纬度转 Web Mercator 瓦片坐标。"""
    lat = max(min(lat, 85.0511287798), -85.0511287798)
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_rad = np.radians(lat)
    y = int((1 - np.log(np.tan(lat_rad) + 1 / np.cos(lat_rad)) / np.pi) / 2 * n)
    return x, y


def tile_to_lonlat(x: int, y: int, z: int) -> tuple[float, float]:
    """瓦片左上角转经纬度。"""
    n = 2 ** z
    lon = x / n * 360 - 180
    lat_rad = np.arctan(np.sinh(np.pi * (1 - 2 * y / n)))
    lat = np.degrees(lat_rad)
    return lon, lat


def build_base_map(
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    width: int,
    height: int,
    zoom: int = 7,
) -> np.ndarray:
    """下载高德瓦片并拼接成覆盖目标范围的浅色底图。"""
    x1, y1 = lonlat_to_tile(lon_min, lat_max, zoom)  # 左上
    x2, y2 = lonlat_to_tile(lon_max, lat_min, zoom)  # 右下

    # 统一下载 256x256 瓦片并拼接
    tile_size = 256
    cols = x2 - x1 + 1
    rows = y2 - y1 + 1
    canvas = np.zeros((rows * tile_size, cols * tile_size, 3), dtype=np.uint8)

    for xi, x in enumerate(range(x1, x2 + 1)):
        for yi, y in enumerate(range(y1, y2 + 1)):
            tile = fetch_amap_tile(x, y, zoom)
            if tile is None:
                tile = np.full((tile_size, tile_size, 3), 245, dtype=np.uint8)  # 浅灰兜底
            canvas[yi * tile_size : (yi + 1) * tile_size, xi * tile_size : (xi + 1) * tile_size] = tile

    # 把目标边界映射到像素，裁剪到精确范围
    lon1, lat1 = tile_to_lonlat(x1, y1, zoom)  # 左上
    lon2, lat2 = tile_to_lonlat(x2 + 1, y2 + 1, zoom)  # 右下

    # 线性插值求裁剪像素
    px1 = int((lon_min - lon1) / (lon2 - lon1) * canvas.shape[1])
    px2 = int((lon_max - lon1) / (lon2 - lon1) * canvas.shape[1])
    py1 = int((lat_max - lat1) / (lat2 - lat1) * canvas.shape[0])
    py2 = int((lat_min - lat1) / (lat2 - lat1) * canvas.shape[0])
    px1, px2 = max(0, px1), min(canvas.shape[1], px2)
    py1, py2 = max(0, py1), min(canvas.shape[0], py2)
    cropped = canvas[py1:py2, px1:px2]

    # 缩放到目标分辨率
    img = Image.fromarray(cropped).resize((width, height), Image.Resampling.LANCZOS)
    return np.array(img)


# ---------- 热力图渲染 ----------
def make_heatmap(
    output: Path = Path("coverage_heatmap.png"),
    width: int = 1920,
    height: int = 1080,
    dpi: int = 300,
) -> None:
    # 范围：广东、湖南、湖北、海南
    lon_min, lon_max = 105.0, 119.5
    lat_min, lat_max = 17.0, 33.5

    # 提取坐标与权重
    lats = np.array([d[0] for d in DATA])
    lons = np.array([d[1] for d in DATA])
    weights = np.array([d[2] for d in DATA])

    # 创建高分辨率栅格，然后下采样，使边缘更平滑
    grid_h, grid_w = height * 2, width * 2
    lon_grid = np.linspace(lon_min, lon_max, grid_w)
    lat_grid = np.linspace(lat_min, lat_max, grid_h)
    X, Y = np.meshgrid(lon_grid, lat_grid)

    # 用带权重的二维 KDE 估计密度
    points = np.vstack([lons, lats])
    try:
        kde = gaussian_kde(points, weights=weights, bw_method=0.25)
        Z = kde(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)
    except Exception:
        # 若 scipy 版本不支持 weights，回退到无权重
        kde = gaussian_kde(points, bw_method=0.25)
        Z = kde(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)

    # 归一化并增强对比（让低-中-高差异更明显）
    Z = Z ** 0.6  #  gamma 压缩，避免低值过于发白
    Z = (Z - Z.min()) / (Z.max() - Z.min() + 1e-9)

    # 自定义色带：深蓝紫 → 蓝 → 青 → 绿 → 黄 → 红
    colors = [
        (0.00, 0.00, 0.50, 0.15),  # 深蓝紫，低透明度
        (0.00, 0.30, 0.85, 0.45),  # 蓝
        (0.00, 0.75, 0.85, 0.65),  # 青
        (0.25, 0.80, 0.25, 0.80),  # 绿
        (1.00, 0.85, 0.00, 0.95),  # 黄
        (1.00, 0.15, 0.00, 1.00),  # 红
    ]
    cmap = mcolors.LinearSegmentedColormap.from_list("amap_heatmap", colors, N=256)

    # 热力图 RGBA
    rgba = cmap(Z)
    rgba[..., 3] = np.clip(Z * 0.92 + 0.08, 0, 1)  # 低值半透明，高值饱满

    # 缩放到目标输出分辨率
    heat_img = Image.fromarray((rgba * 255).astype(np.uint8)).resize((width, height), Image.Resampling.LANCZOS)
    rgba = np.array(heat_img).astype(np.float32) / 255.0

    # 下载浅色底图
    base_img = build_base_map(lon_min, lon_max, lat_min, lat_max, width, height, zoom=7)
    base = base_img.astype(np.float32) / 255.0

    # 正片叠底融合：base * heat + base，保持浅色底图可见
    heat_rgb = rgba[..., :3]
    heat_alpha = rgba[..., 3:4]
    blended = base * (1 - heat_alpha * 0.55) + heat_rgb * heat_alpha * 0.85
    blended = np.clip(blended, 0, 1)
    blended_uint8 = (blended * 255).astype(np.uint8)

    # 用 PIL 添加省会城市标记与文字
    pil_img = Image.fromarray(blended_uint8)
    draw = ImageDraw.Draw(pil_img)

    # 尝试加载中文字体，找不到则使用默认字体
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]
    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 22)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    for name, lat, lon in CAPITALS:
        px = int((lon - lon_min) / (lon_max - lon_min) * width)
        py = int((lat_max - lat) / (lat_max - lat_min) * height)
        r = 6
        draw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 60, 40, 255), outline=(40, 40, 40, 255), width=2)
        # 文字带白色描边，提升可读性
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1), (0, 0)]:
            draw.text((px + 12 + dx, py - 12 + dy), name, font=font, fill=(255, 255, 255, 255) if (dx, dy) != (0, 0) else (50, 50, 50, 255))

    pil_img.save(output, "PNG", dpi=(dpi, dpi))
    print(f"已保存: {output.resolve()}")


if __name__ == "__main__":
    make_heatmap()
