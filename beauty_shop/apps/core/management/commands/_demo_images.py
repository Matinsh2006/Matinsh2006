"""Procedurally drawn demo images (products, banners, logos) for ``seed_demo``."""
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WHITE = (255, 255, 255)
GOLD = (212, 175, 105)


def mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2, strict=True))


def lighten(color, t):
    return mix(color, WHITE, t)


def darken(color, t):
    return mix(color, (0, 0, 0), t)


def gradient(size, start, end, horizontal=False):
    mask = Image.linear_gradient("L")
    if horizontal:
        mask = mask.rotate(90)
    mask = mask.resize(size)
    return Image.composite(Image.new("RGB", size, end), Image.new("RGB", size, start), mask)


def _to_file(image, fmt="JPEG"):
    buffer = BytesIO()
    if fmt == "JPEG":
        image.convert("RGB").save(buffer, "JPEG", quality=86, optimize=True, progressive=True)
    else:
        image.save(buffer, "PNG", optimize=True)
    return ContentFile(buffer.getvalue())


def draw_product(layer, kind, cx, top, k, color):
    """Draw a stylised cosmetic product. Units: an 800px tall canvas (y ≈ 160…660)."""
    d = ImageDraw.Draw(layer, "RGBA")
    dark, mid, light = darken(color, 0.45), darken(color, 0.2), lighten(color, 0.6)
    shine = (255, 255, 255, 70)

    def box(x0, y0, x1, y1):
        return [cx + x0 * k, top + y0 * k, cx + x1 * k, top + y1 * k]

    def rr(coords, radius, fill):
        d.rounded_rectangle(box(*coords), radius=radius * k, fill=fill)

    def poly(*points):
        return [(cx + x * k, top + y * k) for x, y in points]

    if kind == "jar":
        rr((-160, 400, 160, 620), 44, color)
        rr((-175, 330, 175, 420), 26, dark)
        rr((-118, 470, 118, 560), 18, light + (235,))
        rr((-140, 425, -112, 600), 14, shine)
    elif kind == "bottle":
        rr((-45, 170, 45, 250), 12, dark)
        rr((-30, 245, 30, 300), 6, mid)
        rr((-120, 290, 120, 650), 50, color)
        rr((-86, 400, 86, 540), 16, light + (235,))
        rr((-100, 320, -72, 620), 14, shine)
    elif kind == "pump":
        rr((-85, 160, 35, 190), 8, dark)
        rr((-16, 185, 16, 262), 6, dark)
        rr((-55, 255, 55, 305), 10, mid)
        rr((-125, 295, 125, 655), 48, color)
        rr((-88, 410, 88, 545), 16, light + (235,))
        rr((-104, 325, -76, 625), 14, shine)
    elif kind == "tube":
        d.polygon(poly((-115, 190), (115, 190), (80, 560), (-80, 560)), fill=color)
        rr((-125, 170, 125, 205), 6, mid)
        rr((-80, 550, 80, 660), 18, dark)
        rr((-68, 290, 68, 440), 14, light + (225,))
    elif kind == "dropper":
        rr((-42, 160, 42, 290), 40, dark)
        rr((-62, 285, 62, 360), 10, GOLD)
        rr((-110, 350, 110, 650), 36, color + (235,))
        rr((-80, 440, 80, 560), 14, light + (235,))
        rr((-92, 370, -66, 630), 12, shine)
    elif kind == "lipstick":
        rr((-75, 440, 75, 660), 18, dark)
        rr((-60, 370, 60, 450), 8, GOLD)
        d.polygon(poly((-48, 374), (48, 374), (48, 250), (-48, 205)), fill=color)
        rr((-75, 520, 75, 532), 2, GOLD)
    elif kind == "mascara":
        rr((-42, 170, 42, 410), 20, dark)
        rr((-48, 400, 48, 420), 4, GOLD)
        rr((-52, 415, 52, 660), 26, color)
        rr((-30, 460, 30, 620), 10, light + (225,))
    elif kind == "compact":
        d.ellipse(box(-200, 240, 200, 640), fill=dark)
        d.ellipse(box(-165, 275, 165, 605), fill=color)
        d.ellipse(box(-135, 300, -45, 360), fill=(255, 255, 255, 90))
    elif kind == "palette":
        rr((-230, 260, 230, 620), 30, dark)
        size, gap, cols, rows = 88, 14, 4, 3
        start_x = -(cols * size + (cols - 1) * gap) / 2
        for row in range(rows):
            for col in range(cols):
                shade = mix(lighten(color, 0.1 + 0.18 * col), darken(color, 0.12 * row), 0.4)
                x0, y0 = start_x + col * (size + gap), 300 + row * (size + gap)
                rr((x0, y0, x0 + size, y0 + size), 12, shade)
    elif kind == "perfume":
        rr((-60, 170, 60, 270), 50, GOLD)
        rr((-40, 262, 40, 302), 6, darken(GOLD, 0.2))
        rr((-170, 290, 170, 640), 40, color + (230,))
        rr((-120, 385, 120, 520), 16, (255, 255, 255, 150))
        rr((-150, 312, -116, 612), 14, (255, 255, 255, 80))


def _shadow(size, cx, y, width, height, blur):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - width / 2, y, cx + width / 2, y + height], fill=(60, 25, 45, 90))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _bubbles(size, circles):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    for x, y, r, alpha in circles:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, alpha))
    return layer


def product_image(kind, color, variant=0):
    """800×800 JPEG. ``variant`` 0/1/2 give a gallery of slightly different shots."""
    size, scale = 800, 2
    canvas = (size * scale, size * scale)
    backgrounds = [
        (lighten(color, 0.9), lighten(color, 0.74)),
        (WHITE, lighten(color, 0.82)),
        (lighten(color, 0.8), lighten(color, 0.62)),
    ]
    base = gradient(canvas, *backgrounds[variant % 3]).convert("RGBA")
    if variant % 3 == 2:
        w = canvas[0]
        base.alpha_composite(_bubbles(canvas, [(w * .18, w * .22, w * .1, 70), (w * .84, w * .3, w * .06, 90), (w * .78, w * .8, w * .12, 50)]))
    base.alpha_composite(_shadow(canvas, canvas[0] / 2, 632 * scale, 460 * scale, 60 * scale, 18 * scale))
    layer = Image.new("RGBA", canvas, (0, 0, 0, 0))
    draw_product(layer, kind, canvas[0] / 2, 0, scale, color)
    if variant % 3 == 1:
        layer = layer.rotate(-8, resample=Image.Resampling.BICUBIC, center=(canvas[0] / 2, canvas[1] / 2))
    elif variant % 3 == 2:
        inset = int(canvas[0] * 0.08)
        layer = layer.crop((inset, inset, canvas[0] - inset, canvas[1] - inset)).resize(canvas, Image.Resampling.LANCZOS)
    base.alpha_composite(layer)
    return _to_file(base.resize((size, size), Image.Resampling.LANCZOS))


def scene_image(size, colors, products, bubbles=True, vertical_center=0.54):
    """Banner / cover: gradient background with a group of products.

    ``products``: list of ``(kind, color, cx_ratio, scale)``.
    """
    width, height = size
    base = gradient(size, colors[0], colors[1], horizontal=True).convert("RGBA")
    if bubbles:
        base.alpha_composite(
            _bubbles(size, [
                (width * .08, height * .2, height * .35, 40),
                (width * .45, height * 1.05, height * .45, 35),
                (width * .92, height * .1, height * .25, 45),
                (width * .3, height * .15, height * .08, 60),
            ])
        )
    for kind, color, cx_ratio, scale in products:
        k = height / 800 * scale
        top = height * vertical_center - 410 * k
        cx = width * cx_ratio
        base.alpha_composite(_shadow(size, cx, top + 632 * k, 440 * k, 55 * k, max(4, 16 * k)))
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        draw_product(layer, kind, cx, top, k, color)
        base.alpha_composite(layer)
    return _to_file(base)


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def logo_image(initial, name, color):
    """400×400 PNG brand logo with an initial and the latin brand name."""
    size = 400
    image = Image.new("RGB", (size, size), WHITE)
    draw = ImageDraw.Draw(image)
    draw.ellipse([60, 40, 340, 320], fill=lighten(color, 0.85), outline=color, width=10)
    draw.text((size / 2, 176), initial, font=_font(150), fill=color, anchor="mm")
    draw.text((size / 2, 362), name.upper(), font=_font(40), fill=darken(color, 0.35), anchor="mm")
    return _to_file(image, "PNG")


def category_image(kind, color):
    """240×240 PNG icon used in the round category cards."""
    size = 240
    base = Image.new("RGBA", (size, size), lighten(color, 0.84) + (255,))
    k = 0.34
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw_product(layer, kind, size / 2, size / 2 - 410 * k, k, color)
    base.alpha_composite(layer)
    return _to_file(base, "PNG")
