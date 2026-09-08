"""Generate the shared standalone-app tab icons as transparent 81px PNG files."""

from pathlib import Path

from PIL import Image, ImageDraw


SIZE = 81
INACTIVE = "#8A8F98"
ACTIVE = "#D0021B"
TARGETS = (
    Path("apps/shenlun-app/src/assets/icons"),
    Path("apps/theory-app/src/assets/icons"),
)


def canvas():
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def today(color: str) -> Image.Image:
    image, draw = canvas()
    draw.rounded_rectangle((17, 17, 64, 64), radius=7, outline=color, width=5)
    draw.line((18, 31, 63, 31), fill=color, width=4)
    draw.line((28, 13, 28, 23), fill=color, width=5)
    draw.line((53, 13, 53, 23), fill=color, width=5)
    draw.line(((27, 49), (37, 57), (54, 40)), fill=color, width=5, joint="curve")
    return image


def study(color: str) -> Image.Image:
    image, draw = canvas()
    draw.line(((40, 63), (33, 59), (25, 57), (17, 57), (17, 22), (26, 23), (34, 26), (40, 29), (40, 63)), fill=color, width=5, joint="curve")
    draw.line(((41, 63), (48, 59), (56, 57), (64, 57), (64, 22), (55, 23), (47, 26), (41, 29)), fill=color, width=5, joint="curve")
    return image


def practice(color: str) -> Image.Image:
    image, draw = canvas()
    draw.line(((22, 64), (22, 17), (61, 17), (61, 51), (48, 64), (22, 64)), fill=color, width=5, joint="curve")
    draw.line(((48, 63), (48, 51), (60, 51)), fill=color, width=4, joint="curve")
    draw.line(((30, 47), (39, 56), (53, 39)), fill=color, width=5, joint="curve")
    return image


def profile(color: str) -> Image.Image:
    image, draw = canvas()
    draw.ellipse((30, 15, 51, 36), outline=color, width=5)
    draw.arc((18, 35, 63, 76), start=185, end=355, fill=color, width=5)
    return image


ICONS = {"today": today, "study": study, "practice": practice, "profile": profile}


for target in TARGETS:
    target.mkdir(parents=True, exist_ok=True)
    for name, renderer in ICONS.items():
        renderer(INACTIVE).save(target / f"{name}.png")
        renderer(ACTIVE).save(target / f"{name}-active.png")

print(f"Generated {len(ICONS) * 2} icons for {len(TARGETS)} standalone apps")
