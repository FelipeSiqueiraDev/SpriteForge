"""Contrato dos frames e exportação sem redimensionar a arte original."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

DIRECTIONS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
SAFE_NAME = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


class ValidationError(ValueError):
    """Um erro verificável no contrato ou nos arquivos de origem."""


def integer(value, label, minimum=1, maximum=4096):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValidationError(f"{label}: inteiro entre {minimum} e {maximum} esperado")
    return value


@dataclass
class Bundle:
    spec: dict
    images: dict
    report: dict


def load_bundle(manifest: Path) -> Bundle:
    manifest = Path(manifest).resolve()
    try:
        spec = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValidationError(f"Não foi possível ler o manifesto: {exc}") from exc
    if not isinstance(spec, dict) or spec.get("version") != 1:
        raise ValidationError("O manifesto precisa ser um objeto com version: 1")
    if not isinstance(spec.get("id"), str) or not SAFE_NAME.fullmatch(spec["id"]):
        raise ValidationError("id: use letras minúsculas, números, hífen ou sublinhado")
    if not isinstance(spec.get("name"), str) or not spec["name"].strip():
        raise ValidationError("name: nome não vazio esperado")
    cell = spec.get("cell")
    if not isinstance(cell, list) or len(cell) != 2:
        raise ValidationError("cell: [largura, altura] esperado")
    width, height = [integer(v, "cell", maximum=512) for v in cell]
    pivot = spec.get("pivot")
    if not isinstance(pivot, list) or len(pivot) != 2:
        raise ValidationError("pivot: [x, y] esperado")
    px = integer(pivot[0], "pivot.x", minimum=0, maximum=width - 1)
    py = integer(pivot[1], "pivot.y", minimum=0, maximum=height - 1)
    animations = spec.get("animations")
    if not isinstance(animations, dict) or not animations:
        raise ValidationError("animations: ao menos uma animação esperada")
    images, rows, warnings = {}, [], []
    for action, clip in animations.items():
        if not SAFE_NAME.fullmatch(action):
            raise ValidationError(f"Nome de animação inválido: {action}")
        if not isinstance(clip, dict):
            raise ValidationError(f"{action}: objeto esperado")
        count = integer(clip.get("frame_count"), f"{action}.frame_count", maximum=64)
        duration = integer(clip.get("duration_ms"), f"{action}.duration_ms", minimum=10, maximum=2000)
        if duration % 10:
            raise ValidationError(f"{action}: duration_ms precisa ser múltiplo de 10 para GIF")
        frames = clip.get("directions")
        if not isinstance(frames, dict) or set(frames) != set(DIRECTIONS):
            raise ValidationError(f"{action}: forneça exatamente as oito direções {DIRECTIONS}")
        for direction in DIRECTIONS:
            paths = frames[direction]
            if not isinstance(paths, list) or len(paths) != count:
                raise ValidationError(f"{action}/{direction}: esperados {count} frames")
            clip_images, boxes = [], []
            for index, relative in enumerate(paths):
                label = f"{action}/{direction}/{index:02d}"
                if not isinstance(relative, str):
                    raise ValidationError(f"{label}: caminho de arquivo esperado")
                path = (manifest.parent / relative).resolve()
                if not path.is_relative_to(manifest.parent):
                    raise ValidationError(f"{label}: o arquivo precisa estar dentro da pasta do personagem")
                try:
                    with Image.open(path) as source:
                        if source.format != "PNG" or source.size != (width, height):
                            raise ValidationError(f"{label}: PNG {width}×{height} esperado; recebido {source.format} {source.size}")
                        image = source.convert("RGBA")
                except (OSError, ValueError) as exc:
                    if isinstance(exc, ValidationError):
                        raise
                    raise ValidationError(f"{label}: não foi possível abrir {relative}: {exc}") from exc
                alpha = image.getchannel("A")
                if not set(alpha.get_flattened_data()).issubset({0, 255}):
                    raise ValidationError(f"{label}: alpha parcial; pixel art precisa de transparência binária")
                bbox = alpha.getbbox()
                if not bbox:
                    raise ValidationError(f"{label}: frame vazio")
                x0, y0, x1, y1 = bbox
                if x0 == 0 or y0 == 0 or x1 == width or y1 == height:
                    raise ValidationError(f"{label}: desenho encosta na borda; mantenha margem de pelo menos 1 pixel")
                if alpha.getextrema()[0] == 255:
                    raise ValidationError(f"{label}: fundo sem transparência")
                colors = len({rgba for rgba in image.get_flattened_data() if rgba[3]})
                if colors > 64:
                    warnings.append(f"{label}: {colors} cores visíveis; revisar paleta e possível antialiasing")
                if abs(y1 - 1 - py) > 6:
                    warnings.append(f"{label}: último pixel visível está a mais de 6 px do pivot.y; revisar pés/objetos")
                rows.append({"action": action, "direction": direction, "index": index,
                             "source": relative, "bbox": list(bbox), "visible_colors": colors,
                             "ground_offset_px": y1 - 1 - py})
                boxes.append(bbox)
                clip_images.append(image)
            if max(b[1] for b in boxes) - min(b[1] for b in boxes) > 4:
                warnings.append(f"{action}/{direction}: topo varia mais de 4 px; revisar proporção/bounce")
            if count > 1 and len({im.tobytes() for im in clip_images}) == 1:
                warnings.append(f"{action}/{direction}: todos os frames são idênticos")
            images[action, direction] = clip_images
    report = {"id": spec["id"], "frame_count": len(rows), "pivot": [px, py],
              "warnings": warnings, "frames": rows,
              "visual_review_required": ["identidade", "ângulo de câmera", "anatomia",
                                         "contato dos pés", "continuidade do loop", "detalhes de roupa/rosto"]}
    return Bundle(spec, images, report)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_bundle(bundle: Bundle, destination: Path):
    spec = bundle.spec
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    width, height = spec["cell"]
    atlas = {"version": 1, "id": spec["id"], "cell": spec["cell"], "pivot": spec["pivot"],
             "direction_order": list(DIRECTIONS), "animations": {}}
    # Nenhum resize, crop ou ajuste automático é feito na arte de origem.
    for action, clip in spec["animations"].items():
        count = clip["frame_count"]
        sheet = Image.new("RGBA", (width * count, height * len(DIRECTIONS)))
        atlas_clip = {"sheet": f"{action}.png", "duration_ms": clip["duration_ms"], "directions": {}}
        for row, direction in enumerate(DIRECTIONS):
            frames = bundle.images[action, direction]
            frame_dir = destination / "frames" / action / direction
            frame_dir.mkdir(parents=True, exist_ok=True)
            entries = []
            for col, frame in enumerate(frames):
                sheet.paste(frame, (col * width, row * height))
                frame.save(frame_dir / f"{col:02d}.png")
                entries.append({"x": col * width, "y": row * height, "w": width, "h": height,
                                "pivot": spec["pivot"], "duration_ms": clip["duration_ms"]})
            atlas_clip["directions"][direction] = entries
            # GIF é apenas prévia: fundo opaco para evitar halos/trilhas de transparência.
            gif_frames = []
            for frame in frames:
                preview = Image.new("RGBA", frame.size, "#14252c")
                preview.alpha_composite(frame)
                gif_frames.append(preview.convert("RGB").resize((width * 3, height * 3), Image.Resampling.NEAREST))
            gif_frames[0].save(destination / f"{action}-{direction}.gif", save_all=True,
                               append_images=gif_frames[1:], duration=clip["duration_ms"], loop=0,
                               disposal=2, optimize=False)
        sheet.save(destination / f"{action}.png")
        atlas["animations"][action] = atlas_clip
    write_json(destination / "atlas.json", atlas)
    write_json(destination / "report.json", bundle.report)
    render_preview(bundle, atlas, destination / "index.html")


def render_preview(bundle, atlas, path):
    data = json.dumps(atlas, ensure_ascii=False).replace("<", "\\u003c")
    title = html.escape(bundle.spec["name"])
    options = "".join(f'<option value="{a}">{a}</option>' for a in atlas["animations"])
    template = Path(__file__).with_name("preview.html").read_text(encoding="utf-8")
    page = template.replace("__TITLE__", title).replace("__OPTIONS__", options).replace("__ATLAS__", data)
    path.write_text(page, encoding="utf-8")
