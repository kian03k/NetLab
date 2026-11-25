# -*- coding: utf-8 -*-
"""
NetLab 应用图标生成脚本
========================
生成 256×256 多尺寸 .ico 图标，设计语言对齐 netops。

视觉构成（自底向上 5 层）：
  ① 蓝色渐变圆角矩形背景  #3B82F6→#1D4ED8 垂直渐变
  ② 白色圆角内框
  ③ 居中粗体 "N"          Segoe UI Bold，颜色 #2563EB
  ④ 右上角三节点网络点缀   等边小三角形（≥64px 才绘制）
  ⑤ 圆角外全透明
所有参数以比例定义，缩放时自动适配，无需逐尺寸微调。

用法：python tools/generate_icon.py [--output app.ico] [--compare app.ico]
"""
import argparse
import os
import struct
import io
from PIL import Image, ImageDraw, ImageFont

# ── 设计参数（比例，相对画布尺寸） ──────────────────────────
CANVAS = 256
MARGIN_RATIO = 0.06       # 透明边距
RADIUS_RATIO = 0.22       # 圆角半径（相对矩形宽度）
BORDER_RATIO = 0.04       # 边框宽度
N_FONT_RATIO = 0.52       # N 字号

# 配色
GRADIENT_TOP = (59, 130, 246)      # #3B82F6
GRADIENT_BOTTOM = (29, 78, 216)    # #1D4ED8
N_COLOR = (37, 99, 235)            # #2563EB
MOTIF_COLOR = (37, 99, 235)        # #2563EB

# 网络点缀（三节点等边三角形，按比例定位）
MOTIF_MIN_SIZE = 64
MOTIF_CX_RATIO = 0.72              # 三角形中心 x
MOTIF_CY_RATIO = 0.28              # 三角形中心 y
MOTIF_SPREAD_RATIO = 0.035         # 三角形外接圆半径

# 字体回退链（兼容精简版 Windows）
FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold
    "C:/Windows/Fonts/seguisb.ttf",    # Segoe UI Semibold
    "C:/Windows/Fonts/arialbd.ttf",    # Arial Bold
    "C:/Windows/Fonts/ariblk.ttf",     # Arial Black
    "C:/Windows/Fonts/calibrib.ttf",   # Calibri Bold
]

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def rgba(rgb: tuple[int, int, int], a: int = 255) -> tuple[int, int, int, int]:
    return (*rgb, a)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """按回退链加载粗体字体。"""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_gradient(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """垂直线性渐变，逐行插值。"""
    grad = Image.new('RGB', (width, height))
    px = grad.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(width):
            px[x, y] = (r, g, b)
    return grad


def draw_icon(size: int) -> Image.Image:
    """绘制指定尺寸的图标，返回 RGBA Image。"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 按比例计算几何参数
    margin = max(1, round(size * MARGIN_RATIO))
    rect_w = size - 2 * margin
    radius = max(1, round(rect_w * RADIUS_RATIO))
    border = max(1, round(size * BORDER_RATIO))
    inner_margin = margin + border
    inner_r = max(0, radius - border)

    # ① 蓝色渐变圆角矩形
    grad = make_gradient(rect_w, rect_w, GRADIENT_TOP, GRADIENT_BOTTOM)
    mask = Image.new('L', (rect_w, rect_w), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, rect_w - 1, rect_w - 1), radius=radius, fill=255
    )
    img.paste(grad, (margin, margin), mask)

    # ② 白色圆角内框
    draw.rounded_rectangle(
        (inner_margin, inner_margin, size - inner_margin - 1, size - inner_margin - 1),
        radius=inner_r, fill=rgba((255, 255, 255))
    )

    # ③ 居中 "N"（精确居中，减去 bbox 左上偏移）
    font_size = max(8, round(size * N_FONT_RATIO))
    font = load_font(font_size)
    bbox = draw.textbbox((0, 0), "N", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1]
    draw.text((tx, ty), "N", fill=rgba(N_COLOR), font=font)

    # ④ 三节点网络点缀（等边三角形，≥64px 才绘制）
    if size >= MOTIF_MIN_SIZE:
        cx = round(size * MOTIF_CX_RATIO)
        cy = round(size * MOTIF_CY_RATIO)
        spread = max(3, round(size * MOTIF_SPREAD_RATIO))
        dot_r = max(1, round(spread * 0.25))
        lw = max(1, round(spread * 0.15))
        # 等边三角形：顶点在上，两底点在下
        nodes = [
            (cx, cy - spread),
            (cx - round(spread * 0.866), cy + round(spread * 0.5)),
            (cx + round(spread * 0.866), cy + round(spread * 0.5)),
        ]
        # 先画连线（在节点下方）
        for i in range(3):
            for j in range(i + 1, 3):
                draw.line([nodes[i], nodes[j]], fill=rgba(MOTIF_COLOR), width=lw)
        # 再画节点圆点
        for nx, ny in nodes:
            draw.ellipse((nx - dot_r, ny - dot_r, nx + dot_r, ny + dot_r),
                         fill=rgba(MOTIF_COLOR))

    return img


def generate_ico(output_path: str) -> Image.Image:
    """生成多尺寸 .ico：每个尺寸独立绘制，再打包。"""
    frames = [draw_icon(s) for s in ICO_SIZES]
    # 必须以最大尺寸作主图：Pillow 会跳过比主图更大的尺寸，用 16px 当主图只会剩 1 帧。
    # 各尺寸都有独立绘制的帧，Pillow 按尺寸精确匹配取用，不做缩放。
    frames[-1].save(output_path, format='ICO', sizes=[(s, s) for s in ICO_SIZES],
                    append_images=frames[:-1])
    return frames[-1]


def compare_icons(new_path: str, old_path: str) -> float:
    """逐像素对比两个 .ico 的 256×256 帧，返回一致率。"""
    os.makedirs("tmp", exist_ok=True)

    def load_max_frame(path: str) -> Image.Image:
        data = open(path, 'rb').read()
        _, _, count = struct.unpack('<HHH', data[:6])
        off = 6
        frames = []
        for i in range(count):
            w, h, _, _, _, _, sz, oft = struct.unpack('<BBBBHHII', data[off:off + 16])
            off += 16
            w = 256 if w == 0 else w
            h = 256 if h == 0 else h
            frames.append((w, sz, oft))
        frames.sort(reverse=True)
        W2, sz, oft = frames[0]
        return Image.open(io.BytesIO(data[oft:oft + sz])).convert('RGBA')

    img_old = load_max_frame(old_path)
    img_new = load_max_frame(new_path)

    assert img_old.size == img_new.size == (256, 256), \
        f"Size mismatch: {img_old.size} vs {img_new.size}"

    px_old = img_old.load()
    px_new = img_new.load()

    total = 256 * 256
    exact_match = 0
    close_match = 0
    diff_pixels = 0
    max_diff = 0

    for y in range(256):
        for x in range(256):
            p1 = px_old[x, y]
            p2 = px_new[x, y]
            if p1 == p2:
                exact_match += 1
            else:
                d = max(abs(a - b) for a, b in zip(p1, p2))
                max_diff = max(max_diff, d)
                if d <= 10:
                    close_match += 1
                else:
                    diff_pixels += 1

    # 差异可视化：灰=一致，绿=小差异，红=显著差异
    diff_img = Image.new('RGB', (256, 256), (0, 0, 0))
    diff_px = diff_img.load()
    for y in range(256):
        for x in range(256):
            p1, p2 = px_old[x, y], px_new[x, y]
            if p1 == p2:
                diff_px[x, y] = (128, 128, 128)
            else:
                d = max(abs(a - b) for a, b in zip(p1, p2))
                diff_px[x, y] = (0, 255, 0) if d <= 10 else (255, 0, 0)
    diff_img.save('tmp/icon_diff.png')
    img_new.save('tmp/icon_new_256.png')

    print(f"总像素: {total}")
    print(f"完全相同: {exact_match} ({exact_match/total*100:.2f}%)")
    print(f"小差异(≤10): {close_match} ({close_match/total*100:.2f}%)")
    print(f"显著差异(>10): {diff_pixels} ({diff_pixels/total*100:.2f}%)")
    print(f"最大单通道差异: {max_diff}")

    return exact_match / total


def main():
    parser = argparse.ArgumentParser(description='生成 NetLab 应用图标')
    parser.add_argument('--output', '-o', default='app.ico', help='输出路径')
    parser.add_argument('--compare', '-c', default=None, help='对比已有 .ico')
    args = parser.parse_args()

    print(f"生成图标 → {args.output}")
    main_img = generate_ico(args.output)
    print(f"  256×256 主图: {main_img.size}")
    print(f"  多尺寸: {ICO_SIZES}")
    print(f"  文件大小: {os.path.getsize(args.output)} bytes")

    if args.compare:
        if os.path.exists(args.compare):
            print(f"\n对比原始图标: {args.compare}")
            match_rate = compare_icons(args.output, args.compare)
            print(f"\n完全一致率: {match_rate*100:.2f}%")
        else:
            print(f"\n对比文件 {args.compare} 不存在，跳过对比")


if __name__ == '__main__':
    main()
