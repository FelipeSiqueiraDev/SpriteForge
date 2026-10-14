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
INK = (62, 49, 40)
# Cinco tons por cor de material; a luz continua fixa no mundo, sem glow.
TONE_FACTORS = np.array([.48, .64, .79, .94, 1.06])
HEAD_CENTER_Z = 55.4
HEAD_RADII = (7.2, 6.1, 8.1)  # Topo continua z=63.5: mesma altura física do perfil CRONA.
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
        self.normals = []

    def triangle(self, points, color, part, normals=None):
        self.triangles.append((points, color, part))
        self.normals.append(normals)

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
                for vertices in ([points[row][col], points[row+1][col], points[row+1][n]],
                                 [points[row][col], points[row+1][n], points[row][n]]):
                    normals = (np.array(vertices)-center)/np.square(radii)
                    normals /= np.linalg.norm(normals, axis=1)[:,None]
                    self.triangle(vertices, color, part, normals)

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
            for vertices in ([points[0][i], points[1][i], points[1][n]],
                             [points[0][i], points[1][n], points[0][n]]):
                normals = []
                for vertex in vertices:
                    offset = vertex-a
                    normal = offset-axis*float(offset@axis)
                    normals.append(normal/np.linalg.norm(normal))
                self.triangle(vertices, color, part, normals)
        # Caps são achatadas; os volumes das articulações fazem a transição.
        for row, center in enumerate((a, b)):
            for i in range(8):
                order = (i, (i+1) % 8) if row else ((i+1) % 8, i)
                self.triangle([center, points[row][order[0]], points[row][order[1]]], color, part)

    def box(self, center, radii, color, part="body"):
        center, radii = np.array(center), np.array(radii)
        corners = [center+radii*np.array(signs) for signs in
                   ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                    (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
        for a,b,c,d in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.triangle([corners[a],corners[b],corners[c]],color,part)
            self.triangle([corners[a],corners[c],corners[d]],color,part)

    def foot(self, center, radii, color, part="body"):
        """Base plana, ponta baixa e quinas chanfradas: o pé não vira um bloco."""
        center, radii=np.array(center),np.array(radii)
        ring=np.array([(-.75,-1),(.75,-1),(1,-.6),(1,.65),(.75,1),(-.75,1),(-1,.65),(-1,-.6)])
        bottom=[center+np.array([x*radii[0],y*radii[1],-radii[2]]) for x,y in ring]
        top=[center+np.array([x*radii[0]*.88,y*radii[1]*.93,radii[2]*(.9-.6*max(0,y))]) for x,y in ring]
        upper=center+np.array([0,0,radii[2]*.65])
        lower=center+np.array([0,0,-radii[2]])
        for i in range(8):
            n=(i+1)%8
            self.triangle([lower,bottom[n],bottom[i]],color,part)
            self.triangle([upper,top[i],top[n]],color,part)
            self.triangle([bottom[i],bottom[n],top[n]],color,part)
            self.triangle([bottom[i],top[n],top[i]],color,part)


def build_scene(recipe, current_pose):
    scene = Scene()
    joints, bob = current_pose["joints"], current_pose["bob"]
    skin = recipe["body_color"]
    scene.ellipsoid((0, 0, 26 + bob), (6.8, 4.0, 5.5), skin)
    scene.ellipsoid((0, 0, 35 + bob), (7.8, 4.3, 9.7), skin)
    scene.ellipsoid((0, 0, 45 + bob), (2.5, 2.5, 3.4), skin)
    scene.ellipsoid((0, 0, HEAD_CENTER_Z+bob), HEAD_RADII, skin)
    scene.ellipsoid((0, .3, 50.8+bob), (5.0, 4.8, 3.4), skin)
    for sign in (-1, 1):
        scene.ellipsoid((sign*7.1, 0, 55+bob), (1.0, 1.2, 1.7), skin)
        # Detalhes pertencem ao rosto em 3D: a profundidade os oculta nas costas.
        scene.ellipsoid((sign*2.65, 5.7, 57.2+bob), (.55, .38, .62), "#453a32")
        scene.bone((sign*1.9,5.65,58.3+bob),(sign*3.25,5.1,58.25+bob),.24,"#756351")
    scene.ellipsoid((0, 6.0, 54.8+bob), (.95, 1.3, 1.35), skin)
    scene.bone((-.9,5.03,52.1+bob),(.9,5.03,52.1+bob),.22,"#94705b")
    outfit = recipe.get("outfit") or {}
    for side in ("left", "right"):
        p = lambda joint: joints[side + "_" + joint]
        scene.bone(p("hip"), p("knee"), 3.2, skin)
        scene.bone(p("knee"), p("ankle"), 2.55, skin)
        scene.ellipsoid(p("knee"), (3.2, 3.2, 3.2), skin)
        ankle = np.array(p("ankle"))
        foot = ankle + (0, 1.8, -1.6)
        scene.foot(foot, (2.8, 4.7, 2.4), skin)
        scene.ellipsoid(ankle, (2.55,2.55,3.0), skin)
        scene.bone(p("shoulder"), p("elbow"), 2.7, skin)
        scene.bone(p("elbow"), p("wrist"), 2.0, skin)
        scene.ellipsoid(p("elbow"), (2.7, 2.7, 2.7), skin)
        scene.ellipsoid(np.array(p("wrist"))+(0,.1,-.6), (2.15, 1.85, 3.0), skin)
        scene.ellipsoid(np.array(p("wrist"))+(1.6 if side=='left' else -1.6,1,-.4), (.85,.95,1.45), skin)
        if "shirt" in outfit:
            color = outfit["shirt"]
            scene.bone(p("shoulder"), p("elbow"), 3.15, color, "shirt")
            cuff=np.array(p("wrist"))+(0,0,1.5)
            scene.bone(p("elbow"), cuff, 2.5, color, "shirt")
            scene.ellipsoid(p("elbow"), (3.15, 3.15, 3.15), color, "shirt")
        if "trousers" in outfit:
            color = outfit["trousers"]
            scene.bone(p("hip"), p("knee"), 3.65, color, "trousers")
            scene.bone(p("knee"), p("ankle"), 3.0, color, "trousers")
            scene.ellipsoid(p("knee"), (3.65, 3.65, 3.65), color, "trousers")
        if "boots" in outfit:
            scene.foot(foot, (3.3, 5.15, 2.4), outfit["boots"], "boots")
            scene.ellipsoid(ankle + (0, 0, 1), (3.35, 3.35, 4.4), outfit["boots"], "boots")
            scene.foot(foot+(0,0,-1.8),(3.35,5.2,.6),"#493c34","boots")
    if "trousers" in outfit:
        scene.ellipsoid((0, 0, 25.5 + bob), (7.3, 4.5, 5.8), outfit["trousers"], "trousers")
    if "shirt" in outfit:
        scene.ellipsoid((0, 0, 35 + bob), (8.35, 4.85, 10.1), outfit["shirt"], "shirt")
        # Costura e botões são volumes da camisa; não são desenhados por cima das costas.
        scene.bone((0,4.9,30+bob),(0,4.9,39+bob),.22,outfit["shirt"],"shirt")
        for z in (33,37):
            scene.ellipsoid((0,4.8,z+bob),(.35,.35,.35),"#ccbea5","shirt")
    if recipe.get("hair"):
        scene.ellipsoid((0, -.25, HEAD_CENTER_Z+bob), (7.65, 6.55, 8.6), recipe["hair"], "hair", upper_only=True)
    if recipe.get("beard"):
        scene.ellipsoid((0, 4.7, 50.5 + bob), (4.2, 1.7, 2.5), recipe["beard"], "beard")
    if recipe.get("glasses"):
        color = recipe["glasses"]
        for x in (-2.65, 2.65):
            for z in (55.8, 59):
                scene.bone((x-1.9, 6.35, z+bob), (x+1.9, 6.35, z+bob), .4, color, "glasses")
            for edge in (-1.9, 1.9):
                scene.bone((x+edge, 6.35, 55.8+bob), (x+edge, 6.35, 59+bob), .4, color, "glasses")
        scene.bone((-.75, 6.35, 57.4+bob), (.75, 6.35, 57.4+bob), .4, color, "glasses")
        for sign in (-1, 1):
            scene.bone((sign*4.6, 6.35, 57.4+bob), (sign*7.55, 0, 57.4+bob), .38, color, "glasses")
    if recipe.get("scar"):
        scene.bone((3.6, 5.4, 53+bob), (4.7, 4.6, 55.5+bob), .4, recipe["scar"], "scar")
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
    material_palettes = {}
    # Normais suaves evitam que a malha apareça como manchas triangulares no sprite.
    # A saída continua quantizada: sem antialiasing, sem degradê entre os cinco tons.
    for triangle_index, (local, color, part) in enumerate(scene.triangles):
        world = np.array(local) @ rotation.T
        normal = np.cross(world[1]-world[0], world[2]-world[0])
        length = np.linalg.norm(normal)
        if length < 1e-8:
            continue
        normal /= length
        # A reflexão da base local inverte o winding; usar orientação externa.
        normal *= -1
        if color not in material_palettes:
            rgb = np.array([int(color[i:i+2], 16) for i in (1, 3, 5)])
            warm_shadow = np.array([7, 1, -5])
            material_palettes[color] = np.clip(rgb*TONE_FACTORS[:,None]+warm_shadow*(1-TONE_FACTORS[:,None]),0,255).astype(np.uint8)
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
        part_id = PARTS.index(part)+1
        closer = sample_z > depth[area]+1e-7
        # A tampa de uma manga pode coincidir com a do braço. Nesse empate,
        # a superfície da roupa cobre a pele, sem atravessar volumes mais próximos.
        coplanar = np.isclose(sample_z,depth[area],atol=1e-7,rtol=0) & (part_id > parts[area])
        visible = (w0 >= -1e-7) & (w1 >= -1e-7) & (w2 >= -1e-7) & (closer | coplanar)
        depth[area][visible] = sample_z[visible]
        smooth = scene.normals[triangle_index]
        if smooth is None:
            lighting = np.full(w0.shape,max(0,float(normal@LIGHT)))
        else:
            normals = np.array(smooth)@rotation.T
            interpolated = w0[...,None]*normals[0]+w1[...,None]*normals[1]+w2[...,None]*normals[2]
            interpolated /= np.maximum(np.linalg.norm(interpolated,axis=-1)[...,None],1e-8)
            lighting = np.maximum(0,interpolated@LIGHT)
        tone = np.clip(np.floor(lighting*5).astype(int),0,4)
        rgba[area][visible,:3] = material_palettes[color][tone[visible]]
        rgba[area][visible,3] = 255
        parts[area][visible] = part_id
    # Contato entre volumes e bordas de materiais: um único pixel do lado mais escuro.
    opaque = rgba[:,:,3] > 0
    edges = np.zeros(opaque.shape,dtype=bool)
    for dy,dx in ((0,1),(1,0),(0,-1),(-1,0)):
        neighbor_alpha=np.roll(opaque,(dy,dx),(0,1))
        neighbor_parts=np.roll(parts,(dy,dx),(0,1))
        neighbor_depth=np.roll(depth,(dy,dx),(0,1))
        depth_difference=np.zeros_like(depth)
        shared=opaque & neighbor_alpha
        np.subtract(neighbor_depth,depth,out=depth_difference,where=shared)
        edges |= shared & (((neighbor_parts!=parts)&(depth_difference>=0)) | (depth_difference>3.2))
    rgba[edges,:3]=INK
    image = Image.fromarray(rgba)
    silhouette = image.getchannel("A")
    expanded = silhouette.filter(ImageFilter.MaxFilter(3))
    outline = Image.new("RGBA", CELL, (*INK,255))
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
    write_json(root / "rig.json", {"version": 1, "base": "humanoid-v2-study", "elevation_degrees": 30,
               "art_style": "cozy-pixel-v2", "material_tones": 5, "outline_pixels": 1,
               "profile": "crona-iso-v1", "crona_commit": CRONA_COMMIT,
               "engine_to_sheet": list(ENGINE_TO_SHEET), "metres_per_model_unit": METRES_PER_MODEL_UNIT,
               "part_ids": {str(i+1): name for i, name in enumerate(PARTS)},
               "pose_coordinates": "local: x=right, y=forward, z=up",
               "stride_world_units_per_loop": 22, "walk_loop_ms": 600,
               "poses": pose_records})
    return root / "manifest.json"
