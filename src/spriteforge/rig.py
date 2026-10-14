"""Corpo-base volumétrico e articulado com rasterização pixel a pixel.

Mesma geometria, câmera e pose para todas as aparências. A profundidade decide
o que fica na frente: não é uma colagem de acessórios sobre o sprite inteiro.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from .core import DIRECTIONS, SAFE_NAME, ValidationError, write_json
from .crona import CELL, PIVOT, ELEVATION, METRES_PER_MODEL_UNIT, CRONA_COMMIT, ENGINE_TO_SHEET, project_model

LIGHT = np.array([-0.45, 0.35, 0.82])
LIGHT /= np.linalg.norm(LIGHT)
PARTS = ("body", "shirt", "trousers", "boots", "hair", "beard", "glasses", "scar")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


def validate_recipe(recipe):
    if not isinstance(recipe, dict) or recipe.get("version") != 1:
        raise ValidationError("Receita precisa de version: 1")
    if not isinstance(recipe.get("id"), str) or not SAFE_NAME.fullmatch(recipe["id"]):
        raise ValidationError("ID da receita inválido")
    if not isinstance(recipe.get("name"), str) or not recipe["name"].strip():
        raise ValidationError("Nome da receita inválido")
    allowed = {"version", "id", "name", "body_color", "outfit", "hair", "beard", "glasses", "scar"}
    if set(recipe) - allowed:
        raise ValidationError(f"Campos não suportados na receita: {sorted(set(recipe) - allowed)}")
    for key in ("body_color", "hair", "beard", "glasses", "scar"):
        value = recipe.get(key)
        if key == "body_color" and value is None:
            raise ValidationError("body_color é obrigatório")
        if value is not None and (not isinstance(value, str) or not HEX_COLOR.fullmatch(value)):
            raise ValidationError(f"{key}: cor #RRGGBB esperada")
    outfit = recipe.get("outfit")
    if outfit is not None:
        if not isinstance(outfit, dict) or set(outfit) - {"shirt", "trousers", "boots"}:
            raise ValidationError("outfit aceita shirt, trousers e boots")
        for key, color in outfit.items():
            if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
                raise ValidationError(f"outfit.{key}: cor #RRGGBB esperada")
    return recipe


def pose(action, index):
    if action not in ("idle", "walk"):
        raise ValidationError("Rig inicial suporta idle e walk")
    count = 4 if action == "idle" else 6
    if type(index) is not int or not 0 <= index < count:
        raise ValidationError("Índice de pose inválido")
    phase = index * math.tau / count
    # Contato inicial de um pé; três poses depois, contato do pé oposto.
    bob = 0.25 * math.sin(phase) if action == "idle" else -0.8 * abs(math.sin(phase))
    joints = {"hips": [0, 0, 25 + bob], "chest": [0, 0, 35 + bob],
              "neck": [0, 0, 44 + bob], "head": [0, 0, 53 + bob]}
    contacts = {}
    for side, x, offset in (("right", 4.6, 0), ("left", -4.6, math.pi)):
        p = phase + offset
        step = 0 if action == "idle" else 5.5 * math.cos(p)
        lift = 0 if action == "idle" else max(0, -math.sin(p)) * 3.8
        hip = np.array([x, 0, 25 + bob])
        ankle = np.array([x, step, 4 + lift])
        # Duas pernas articuladas de 11.2 unidades, com joelho para a frente.
        delta = ankle - hip
        distance = float(np.linalg.norm(delta))
        axis = delta / distance
        along = distance / 2
        bend = math.sqrt(max(0, 11.2**2 - along**2))
        perpendicular = np.array([0, -axis[2], axis[1]])
        knee = hip + axis * along + perpendicular * bend
        joints[side + "_hip"] = hip.tolist()
        joints[side + "_knee"] = knee.tolist()
        joints[side + "_ankle"] = ankle.tolist()
        joints[side + "_shoulder"] = [x * 1.85, 0, 40 + bob]
        joints[side + "_elbow"] = [x * 2.10, -step * .30 + 1, 32 + bob]
        joints[side + "_wrist"] = [x * 2.16, -step * .6, 24.5 + bob]
        contacts[side] = lift < 0.01
    return {"joints": joints, "contacts": contacts, "bob": bob}


class Scene:
    def __init__(self):
        self.triangles = []

    def ellipsoid(self, center, radii, color, part="body", upper_only=False):
        center = np.array(center)
        points = []
        rings, segments = 8, 12
        for progress in np.linspace(0, 1, rings + 1):
            ring = []
            for a in np.linspace(0, math.tau, segments, endpoint=False):
                end = math.pi * (.5-.1*max(0, math.sin(a))+.12*max(0, -math.sin(a))) if upper_only else math.pi
                latitude = progress * end
                ring.append(center + np.array([math.sin(latitude) * math.cos(a) * radii[0],
                            math.sin(latitude) * math.sin(a) * radii[1], math.cos(latitude) * radii[2]]))
            points.append(ring)
        for row in range(rings):
            for col in range(segments):
                n = (col + 1) % segments
                self.triangles.append(([points[row][col], points[row+1][col], points[row+1][n]], color, part))
                self.triangles.append(([points[row][col], points[row+1][n], points[row][n]], color, part))

    def bone(self, a, b, radius, color, part="body"):
        a, b = np.array(a), np.array(b)
        axis = b - a
        axis /= np.linalg.norm(axis)
        helper = np.array([1., 0., 0.]) if abs(axis[0]) < .9 else np.array([0., 1., 0.])
        u = np.cross(axis, helper)
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        points = [[center + radius * (u * math.cos(angle) + v * math.sin(angle))
                   for angle in np.linspace(0, math.tau, 8, endpoint=False)] for center in (a, b)]
        for i in range(8):
            n = (i + 1) % 8
            self.triangles.append(([points[0][i], points[1][i], points[1][n]], color, part))
            self.triangles.append(([points[0][i], points[1][n], points[0][n]], color, part))
        # Caps são achatadas; os volumes das articulações fazem a transição.
        for row, center in enumerate((a, b)):
            for i in range(8):
                order = (i, (i+1) % 8) if row else ((i+1) % 8, i)
                self.triangles.append(([center, points[row][order[0]], points[row][order[1]]], color, part))


def build_scene(recipe, current_pose):
    scene = Scene()
    joints, bob = current_pose["joints"], current_pose["bob"]
    skin = recipe["body_color"]
    scene.ellipsoid((0, 0, 26 + bob), (7.5, 4.4, 5.5), skin)
    scene.ellipsoid((0, 0, 35 + bob), (8.2, 4.6, 9.7), skin)
    scene.ellipsoid((0, 0, 44 + bob), (2.8, 2.8, 3.4), skin)
    scene.ellipsoid(joints["head"], (9.2, 7.8, 10.5), skin)
    for sign in (-1, 1):
        scene.ellipsoid((sign*9.1, 0, 52 + bob), (1.4, 1.5, 2), skin)
    scene.ellipsoid((0, 7.7, 52 + bob), (1.25, 1.7, 1.5), skin)
    outfit = recipe.get("outfit") or {}
    for side in ("left", "right"):
        p = lambda joint: joints[side + "_" + joint]
        scene.bone(p("hip"), p("knee"), 3.6, skin)
        scene.bone(p("knee"), p("ankle"), 2.9, skin)
        scene.ellipsoid(p("knee"), (3.6, 3.6, 3.6), skin)
        ankle = np.array(p("ankle"))
        foot = ankle + (0, 1.8, -1.6)
        scene.ellipsoid(foot, (3.2, 5.2, 2.4), skin)
        scene.bone(p("shoulder"), p("elbow"), 3.0, skin)
        scene.bone(p("elbow"), p("wrist"), 2.3, skin)
        scene.ellipsoid(p("elbow"), (3, 3, 3), skin)
        scene.ellipsoid(p("wrist"), (2.6, 2.3, 3.2), skin)
        if "shirt" in outfit:
            color = outfit["shirt"]
            scene.bone(p("shoulder"), p("elbow"), 3.55, color, "shirt")
            scene.bone(p("elbow"), p("wrist"), 2.85, color, "shirt")
            scene.ellipsoid(p("elbow"), (3.5, 3.5, 3.5), color, "shirt")
        if "trousers" in outfit:
            color = outfit["trousers"]
            scene.bone(p("hip"), p("knee"), 4.05, color, "trousers")
            scene.bone(p("knee"), p("ankle"), 3.35, color, "trousers")
            scene.ellipsoid(p("knee"), (4.05, 4.05, 4.05), color, "trousers")
        if "boots" in outfit:
            scene.ellipsoid(foot, (3.7, 5.65, 2.8), outfit["boots"], "boots")
            scene.ellipsoid(ankle + (0, 0, 1), (3.35, 3.35, 4.4), outfit["boots"], "boots")
    if "trousers" in outfit:
        scene.ellipsoid((0, 0, 25.5 + bob), (8, 4.9, 5.8), outfit["trousers"], "trousers")
    if "shirt" in outfit:
        scene.ellipsoid((0, 0, 35 + bob), (8.8, 5.15, 10.1), outfit["shirt"], "shirt")
    if recipe.get("hair"):
        scene.ellipsoid((0, -.4, 53 + bob), (9.8, 8.4, 11.1), recipe["hair"], "hair", upper_only=True)
    if recipe.get("beard"):
        scene.ellipsoid((0, 6.7, 47.5 + bob), (4.8, 2.1, 2.6), recipe["beard"], "beard")
    if recipe.get("glasses"):
        color = recipe["glasses"]
        for x in (-3.5, 3.5):
            for z in (52, 56):
                scene.bone((x-2.5, 8, z+bob), (x+2.5, 8, z+bob), .55, color, "glasses")
            for edge in (-2.5, 2.5):
                scene.bone((x+edge, 8, 52+bob), (x+edge, 8, 56+bob), .55, color, "glasses")
        scene.bone((-1, 8, 54+bob), (1, 8, 54+bob), .55, color, "glasses")
        for sign in (-1, 1):
            scene.bone((sign*6, 8, 54+bob), (sign*9.5, 0, 54+bob), .5, color, "glasses")
    if recipe.get("scar"):
        scene.bone((4.5, 7.3, 50+bob), (6, 6.6, 53+bob), .55, recipe["scar"], "scar")
    return scene


def rasterize(scene, direction):
    if direction not in DIRECTIONS:
        raise ValidationError("Direção do rig inválida")
    theta = DIRECTIONS.index(direction) * math.pi / 4
    # Local x = direita do corpo, local y = frente do corpo; N = cima da tela.
    rotation = np.array([[math.cos(theta), math.sin(theta), 0],
                         [math.sin(theta), -math.cos(theta), 0], [0, 0, 1]])
    sin, cos = math.sin(ELEVATION), math.cos(ELEVATION)
    depth = np.full(CELL[::-1], -np.inf)
    rgba = np.zeros((*CELL[::-1], 4), dtype=np.uint8)
    parts = np.zeros(CELL[::-1], dtype=np.uint8)
    # Faces recebem iluminação fixa no mundo e quantização em cinco tons.
    for local, color, part in scene.triangles:
        world = np.array(local) @ rotation.T
        normal = np.cross(world[1]-world[0], world[2]-world[0])
        length = np.linalg.norm(normal)
        if length < 1e-8:
            continue
        normal /= length
        # A reflexão da base local inverte o winding; usar orientação externa.
        normal *= -1
        brightness = .62 + .38 * round(max(0, float(normal @ LIGHT)) * 4) / 4
        rgb = np.array([int(color[i:i+2], 16) for i in (1, 3, 5)])
        shade = np.clip(rgb * brightness, 0, 255).astype(np.uint8)
        projected = project_model(world)
        z = world[:, 1]*cos + world[:, 2]*sin
        low = np.floor(projected.min(axis=0)).astype(int)
        high = np.ceil(projected.max(axis=0)).astype(int)
        x0, y0 = np.maximum(low, 0)
        x1, y1 = np.minimum(high, np.array(CELL)-1)
        if x1 < x0 or y1 < y0:
            continue
        xx, yy = np.meshgrid(np.arange(x0, x1+1)+.5, np.arange(y0, y1+1)+.5)
        a, b, c = projected
        denominator = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
        if abs(denominator) < 1e-8:
            continue
        w0 = ((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/denominator
        w1 = ((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/denominator
        w2 = 1-w0-w1
        sample_z = w0*z[0]+w1*z[1]+w2*z[2]
        area = np.s_[y0:y1+1, x0:x1+1]
        visible = (w0 >= -1e-7) & (w1 >= -1e-7) & (w2 >= -1e-7) & (sample_z > depth[area])
        depth[area][visible] = sample_z[visible]
        rgba[area][visible] = [*shade, 255]
        parts[area][visible] = PARTS.index(part)+1
    image = Image.fromarray(rgba)
    silhouette = image.getchannel("A")
    expanded = silhouette.filter(ImageFilter.MaxFilter(3))
    outline = Image.new("RGBA", CELL, "#353b3d")
    outline.putalpha(expanded)
    outline.alpha_composite(image)
    return outline, parts


def render(recipe, direction, action, index):
    validate_recipe(recipe)
    current = pose(action, index)
    image, visible_parts = rasterize(build_scene(recipe, current), direction)
    return image, visible_parts, current


def generate_rig(recipe_path: Path, output: Path):
    try:
        recipe = validate_recipe(json.loads(Path(recipe_path).read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(f"Receita não pôde ser lida: {exc}") from exc
    root = Path(output) / recipe["id"]
    root.mkdir(parents=True, exist_ok=True)
    animations, pose_records = {}, {}
    for action, count, duration in (("idle", 4, 200), ("walk", 6, 100)):
        directions = {}
        for direction in DIRECTIONS:
            paths = []
            for index in range(count):
                image, parts, current = render(recipe, direction, action, index)
                relative = f"frames/{action}/{direction}/{index:02d}.png"
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                image.save(path)
                # Máscaras de visibilidade para diagnosticar ocultação, não camadas finais de desenho.
                mask = root / "parts" / action / direction / f"{index:02d}.png"
                mask.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(parts).save(mask)
                paths.append(relative)
                pose_records[f"{action}/{direction}/{index:02d}"] = current
            directions[direction] = paths
            print(f"{recipe['id']}: {action}/{direction} pronto", flush=True)
        animations[action] = {"frame_count": count, "duration_ms": duration, "directions": directions}
    write_json(root / "manifest.json", {"version": 1, "id": recipe["id"], "name": recipe["name"],
               "cell": list(CELL), "pivot": list(PIVOT), "animations": animations})
    write_json(root / "appearance.json", recipe)
    write_json(root / "rig.json", {"version": 1, "base": "humanoid-v1-study", "elevation_degrees": 30,
               "profile": "crona-iso-v1", "crona_commit": CRONA_COMMIT,
               "engine_to_sheet": list(ENGINE_TO_SHEET), "metres_per_model_unit": METRES_PER_MODEL_UNIT,
               "part_ids": {str(i+1): name for i, name in enumerate(PARTS)},
               "pose_coordinates": "local: x=right, y=forward, z=up",
               "stride_world_units_per_loop": 22, "walk_loop_ms": 600,
               "poses": pose_records})
    return root / "manifest.json"
