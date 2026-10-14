"""Perfil de projeção e exportação do CRONA, conferido no commit f08bea38.

Nomes N/NE/... são direções da tela. Os números 0..7 do jogo são direções
da grade e precisam do mapeamento explícito abaixo.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

from .core import DIRECTIONS, ValidationError, write_json

CRONA_COMMIT = "f08bea3816fe2af49a98975341b0c6fe4eebf158"
TILE_W, TILE_H, Z_PX = 64, 32, 32
METRES_PER_TILE = .75
ELEVATION = math.radians(30)
Z_PER_METRE = math.sqrt(2) * math.cos(ELEVATION) / METRES_PER_TILE
VERTICAL_PX_PER_METRE = Z_PX * Z_PER_METRE
LEGACY_PERSON_SCALE = VERTICAL_PX_PER_METRE / 57.6
ENGINE_TO_SHEET = ("NE", "E", "SE", "S", "SW", "W", "NW", "N")
ENGINE_VECTORS = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))
SHEET_TO_WORLD = {sheet: ENGINE_VECTORS[index] for index, sheet in enumerate(ENGINE_TO_SHEET)}
# O topo do corpo neutro fica em z=63.5. A escala muda a rasterização, não redimensiona PNGs prontos.
MODEL_HEIGHT_UNITS = 63.5
METRES_PER_MODEL_UNIT = 1.8 / MODEL_HEIGHT_UNITS
CELL, PIVOT = (128, 128), (64, 112)


def iso(x, y, z=0):
    """Coordenadas do CRONA: x/y em casas, z em unidades de altura."""
    return np.stack(((x-y)*(TILE_W/2), (x+y)*(TILE_H/2)-z*Z_PX), axis=-1)


def model_to_map(points):
    """Base do modelo alinhada à câmera → x/y em casas, z no formato do jogo."""
    points = np.asarray(points, dtype=float) * METRES_PER_MODEL_UNIT
    u, v, z = points[..., 0], points[..., 1], points[..., 2]
    return np.stack(((u+v)/math.sqrt(2)/METRES_PER_TILE,
                     (v-u)/math.sqrt(2)/METRES_PER_TILE, z*Z_PER_METRE), axis=-1)


def project_model(points, origin=PIVOT):
    world = model_to_map(points)
    return iso(world[..., 0], world[..., 1], world[..., 2]) + origin


def rotate_local(points, direction):
    if direction not in DIRECTIONS:
        raise ValidationError("Direção do perfil CRONA inválida")
    theta = DIRECTIONS.index(direction)*math.pi/4
    rotation = np.array([[math.cos(theta), math.sin(theta), 0],
                         [math.sin(theta), -math.cos(theta), 0], [0, 0, 1]])
    return np.asarray(points, dtype=float) @ rotation.T


def export_crona(bundle, output: Path):
    """Pacote no formato anim.json v2; não instala nem substitui personagens do CRONA."""
    import json

    rig_path = bundle.source_dir / "rig.json"
    if not rig_path.exists():
        raise ValidationError("Exportação CRONA precisa dos metadados do rig")
    rig = json.loads(rig_path.read_text(encoding="utf-8"))
    if rig.get("profile") != "crona-iso-v1":
        raise ValidationError("Rig precisa usar o perfil de câmera crona-iso-v1")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    scale = 1 / LEGACY_PERSON_SCALE
    entries = {}
    width, height = bundle.spec["cell"]
    px, py = bundle.spec["pivot"]
    for direction in DIRECTIONS:
        clipes = {}
        for action, name in (("idle", "parado"), ("walk", "andar")):
            frames = bundle.images[action, direction]
            strip = Image.new("RGBA", (width*len(frames), height))
            feet = []
            for index, frame in enumerate(frames):
                strip.paste(frame, (width*index, 0))
                current = rig["poses"][f"{action}/{direction}/{index:02d}"]
                points = []
                for side in ("left", "right"):
                    ankle = np.array(current["joints"][side+"_ankle"])
                    foot = ankle + (0, 1.8, -4)
                    foot_world = rotate_local(foot, direction)
                    projected = project_model(foot_world, origin=(0, 0))
                    air = max(0, foot[2])*METRES_PER_MODEL_UNIT*VERTICAL_PX_PER_METRE
                    points.append([round(float(projected[0])*scale, 3), round(float(projected[1])*scale, 3), round(air*scale, 3)])
                feet.append(points)
            filename = f"{name}-desarmado-{direction.lower()}.png"
            strip.save(output / filename)
            clip = {"arquivo": filename, "quadros": len(frames), "w": width, "h": height,
                    "ax": px, "ay": py, "laco": True, "pes": feet}
            if action == "walk":
                # RoomView multiplica este valor por ESCALA_ARTE_PESSOA.
                distance_tiles = rig["stride_world_units_per_loop"]*METRES_PER_MODEL_UNIT/METRES_PER_TILE
                clip.update(casasPorCiclo=distance_tiles/LEGACY_PERSON_SCALE, fase=0)
            else:
                clip["ms"] = bundle.spec["animations"][action]["duration_ms"]
            clipes[name] = clip
        entries[direction.lower()] = clipes
    write_json(output / "anim.json", {"versao": 2, "escala": scale, "estados": {"desarmado": entries}})
    write_json(output / "integration.json", {"repository": "FelipeSiqueiraDev/CRONA", "commit": CRONA_COMMIT,
               "profile": "crona-iso-v1", "engine_to_sheet": list(ENGINE_TO_SHEET),
               "tile": [TILE_W, TILE_H], "metres_per_tile": METRES_PER_TILE,
               "vertical_px_per_metre": VERTICAL_PX_PER_METRE,
               "legacy_person_scale": LEGACY_PERSON_SCALE,
               "native_pixel_factor": scale*LEGACY_PERSON_SCALE,
               "status": "estudo técnico; não instalado no jogo"})
