"""Reproduz as imagens de revisão a partir dos frames gerados pelo rig."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

DIRECTIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def read_sprite(path, size):
    with Image.open(path) as sprite:
        return sprite.convert("RGBA").resize(size, Image.Resampling.NEAREST)


def generate(input_dir, output):
    output.mkdir(parents=True, exist_ok=True)
    base = input_dir / "humanoid-base" / "frames"
    outfit = input_dir / "humanoid-outfit-demo" / "frames"
    image = Image.new("RGB", (1152, 632), "#14252c")
    draw = ImageDraw.Draw(image)
    for n, direction in enumerate(DIRECTIONS):
        sprite = read_sprite(base / "idle" / direction / "00.png", (288, 288))
        x, y = n % 4 * 288, n // 4 * 316 + 28
        image.paste(sprite, (x, y), sprite)
        draw.text((x+12, y-19), direction, fill="#f0c461")
    image.save(output / "humanoid-base.png")
    frames = []
    for index in range(6):
        image = Image.new("RGB", (768, 864), "#14252c")
        draw = ImageDraw.Draw(image)
        for n, direction in enumerate(DIRECTIONS):
            x, y = n % 2 * 384, n // 2 * 216
            draw.text((x+8, y+4), f"{direction}  |  BASE                  VESTIDO", fill="#f0c461")
            for side, path in enumerate((base, outfit)):
                sprite = read_sprite(path / "walk" / direction / f"{index:02d}.png", (192, 192))
                image.paste(sprite, (x+side*192, y+20), sprite)
        frames.append(image)
    frames[0].save(output / "humanoid-comparison.gif", save_all=True, append_images=frames[1:],
                   duration=100, loop=0, disposal=2, optimize=False)
    image = Image.new("RGB", (1728, 320), "#14252c")
    draw = ImageDraw.Draw(image)
    for index in range(6):
        sprite = read_sprite(base / "walk" / "SE" / f"{index:02d}.png", (288, 288))
        image.paste(sprite, (index*288, 24), sprite)
        draw.text((index*288+10, 6), f"SE / {index+1}", fill="#f0c461")
    image.save(output / "humanoid-walk-SE.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("demo-input"))
    parser.add_argument("--output", type=Path, default=Path("previews"))
    args = parser.parse_args()
    generate(args.input, args.output)
