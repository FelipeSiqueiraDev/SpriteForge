"""Manequim de diagnóstico reproduzível, não arte final nem gerador de identidade."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

from .core import DIRECTIONS, write_json


def draw_frame(direction, index, idle=False):
    image = Image.new("RGBA", (96, 96))
    draw = ImageDraw.Draw(image)
    theta = DIRECTIONS.index(direction) * math.pi / 4
    forward = (math.sin(theta), -math.cos(theta))
    right = (math.cos(theta), math.sin(theta))
    phase = index * math.tau / (4 if idle else 6)
    stride = 0 if idle else math.cos(phase) * 6
    bounce = max(0, math.sin(phase)) if idle else abs(math.sin(phase)) * 1.5

    def project(side, along, z):
        x = side * right[0] + along * forward[0]
        y = side * right[1] + along * forward[1]
        return round(48 + x), round(80 + y * 0.5 - z)

    # Painter's order: membros mais distantes antes dos próximos.
    legs = []
    arms = []
    for side in (-1, 1):
        step = stride * side
        lift = 0 if idle else max(0, math.sin(phase) * side) * 4
        legs.append((project(side * 5, step, 0)[1], side, step, lift))
        arms.append((project(side * 11, -step, 31)[1], side, -step))
    for _, side, step, lift in sorted(legs):
        points = [project(side * 5, 0, 29 + bounce), project(side * 5, step * .55, 15 + lift),
                  project(side * 5, step, 2 + lift)]
        draw.line(points, fill="#101b28", width=8)
        draw.line(points, fill="#506d86" if side == 1 else "#394e64", width=4)
        foot = project(side * 5, step + 2, lift)
        draw.rectangle((foot[0] - 4, foot[1] - 3, foot[0] + 4, foot[1]), fill="#172331")
    for _, side, swing in sorted(arms):
        points = [project(side * 9, 0, 47 + bounce), project(side * 12, swing * .5, 36 + bounce),
                  project(side * 11, swing, 28 + bounce)]
        draw.line(points, fill="#142333", width=7)
        draw.line(points, fill="#e3b64c" if side == 1 else "#ae8730", width=3)
        hand = points[-1]
        draw.rectangle((hand[0] - 2, hand[1] - 2, hand[0] + 2, hand[1] + 2), fill="#dda87c")
    torso = [project(-8, -3, 48 + bounce), project(8, -3, 48 + bounce),
             project(8, 3, 27 + bounce), project(-8, 3, 27 + bounce)]
    draw.polygon(torso, fill="#c79731", outline="#152331", width=2)
    # Faixa frontal e marcador lateral assimétrico ajudam a ler as direções.
    front = [project(-7, 3, 46 + bounce), project(7, 3, 46 + bounce),
             project(7, 3, 29 + bounce), project(-7, 3, 29 + bounce)]
    if forward[1] >= 0:
        draw.polygon(front, fill="#e7bd53", outline="#152331")
    marker = project(8, 0, 43 + bounce)
    draw.rectangle((marker[0]-1, marker[1]-1, marker[0]+1, marker[1]+2), fill="#6ac5ca")
    head = project(0, 0, 58 + bounce)
    draw.rectangle((head[0]-8, head[1]-9, head[0]+8, head[1]+7), fill="#142333")
    draw.rectangle((head[0]-6, head[1]-7, head[0]+6, head[1]+5), fill="#dda87c")
    nose = project(0, 7, 56 + bounce)
    if forward[1] >= 0 or abs(forward[0]) > .9:
        draw.rectangle((nose[0]-1, nose[1]-1, nose[0]+1, nose[1]+1), fill="#815944")
    else:
        draw.rectangle((head[0]-6, head[1]-7, head[0]+6, head[1]+5), fill="#506d86")
    return image


def generate_demo(output: Path):
    root = Path(output) / "training-dummy"
    animations = {}
    for action, count, duration in (("idle", 4, 200), ("walk", 6, 100)):
        directions = {}
        for direction in DIRECTIONS:
            paths = []
            for index in range(count):
                relative = f"frames/{action}/{direction}/{index:02d}.png"
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                draw_frame(direction, index, idle=action == "idle").save(path)
                paths.append(relative)
            directions[direction] = paths
        animations[action] = {"frame_count": count, "duration_ms": duration, "directions": directions}
    write_json(root / "manifest.json", {"version": 1, "id": "training-dummy",
               "name": "Manequim técnico — não é arte final", "cell": [96, 96], "pivot": [48, 80],
               "animations": animations})
    return root / "manifest.json"
