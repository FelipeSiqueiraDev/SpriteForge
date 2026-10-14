"""Catálogo de skins: o objeto continua sendo do CRONA; a arte é uma entrega separada."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from .core import ValidationError, write_json

ROTATIONS = ("0", "2", "4", "6")


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ValidationError(f"Arquivo de skin inválido: {exc}") from exc


def verify_source(source, lock):
    source = Path(source)
    for relative, expected in lock["files"].items():
        path = source / relative
        if not path.exists():
            raise ValidationError(f"Fonte do renderizador ausente: {relative}")
        digest = hashlib.sha256(path.read_text(encoding="utf-8").rstrip().encode("utf-8")).hexdigest()
        if digest != expected:
            raise ValidationError(f"Renderizador mudou: {relative}. Revisar o perfil antes de exportar novas skins.")


def resolve_skin(definition, skin, rotation, state=0):
    """Escolhe uma vista completa ou devolve None para o desenho procedural do CRONA."""
    if skin is None:
        return None
    if state and str(state) not in skin.get("estados", {}):
        return None
    views = skin.get("giros", {}) if state == 0 else skin["estados"][str(state)].get("giros", {})
    return views.get(str(rotation))


def audit_skins(catalog, skins, root):
    if catalog.get("version") != 1 or not isinstance(catalog.get("objects"), list):
        raise ValidationError("Catálogo precisa de version: 1 e objects")
    root = Path(root).resolve()
    rows, known = [], set()
    for item in catalog["objects"]:
        definition = item["definition"]
        id = item["id"]
        if id in known or id != definition["id"]:
            raise ValidationError(f"ID duplicado ou incompatível: {id}")
        known.add(id)
        skin = skins.get(id)
        missing = []
        if skin:
            if item["type"] != "floor":
                raise ValidationError(f"Skins de parede precisam de vistas l/r: {id}")
            if skin.get("pixel") is not True or skin.get("exato") is not True or skin.get("escala") != 1:
                raise ValidationError(f"{id}: skin precisa ser pixel 1:1 e exata")
            if len(skin.get("real", [])) != 3 or not all(type(v) in (int,float) and math.isfinite(v) and v > 0 for v in skin["real"]):
                raise ValidationError(f"{id}: dimensão física ausente")
            rotations = [str(r) for r in definition.get("rotations", (0,2,4,6))]
            for state in range(definition.get("states", 1)):
                for rotation in rotations:
                    view = resolve_skin(definition, skin, rotation, state)
                    if not view:
                        missing.append(f"estado {state}, giro {rotation}")
                        continue
                    path = (root/view["arquivo"]).resolve()
                    if not path.is_relative_to(root):
                        raise ValidationError(f"{id}: imagem fora da pasta de skins")
                    try:
                        with Image.open(path) as image:
                            if image.format != "PNG" or image.mode != "RGBA":
                                raise ValidationError(f"{id}: PNG RGBA esperado")
                            if not image.getchannel("A").getbbox():
                                raise ValidationError(f"{id}: imagem vazia")
                    except OSError as exc:
                        raise ValidationError(f"{id}: imagem ausente ou inválida: {path.name}") from exc
                    for axis in ("ax", "ay"):
                        if type(view.get(axis)) not in (int,float) or not math.isfinite(view[axis]):
                            raise ValidationError(f"{id}: âncora {axis} inválida")
        status = "ready" if skin and not missing else "partial" if skin else "pending"
        rows.append({"id": id, "name": item["name"], "type": item["type"],
                     "category": definition["category"], "status": status, "missing_views": missing,
                     "fallback": "procedural_crona", "definition": definition,
                     "skin": skin if status == "ready" else None})
    unknown = set(skins)-known
    if unknown:
        raise ValidationError(f"Skins sem objeto no CRONA: {sorted(unknown)}")
    return {"version":1, "objects":rows,
            "summary": {status: sum(r["status"]==status for r in rows) for status in ("ready","partial","pending")}}


def merge_manifest(original, patch):
    """Une só os IDs entregues e preserva a vista tática e o encosto do móvel."""
    merged = dict(original)
    for id, entry in patch.items():
        previous = original.get(id, {})
        keep = {key: previous[key] for key in ("cima", "cimaEstados", "encosta") if key in previous}
        merged[id] = keep | entry
    return merged


def render_gallery(report, output, relative_assets="client/public/arte/mobiliario/"):
    data = json.dumps(report,ensure_ascii=False).replace("<","\\u003c")
    template = Path(__file__).with_name("skin-gallery.html").read_text(encoding="utf-8")
    output.write_text(template.replace("__DATA__",data).replace("__ASSETS__",json.dumps(relative_assets)),encoding="utf-8")


def build_skins(source, profile_path, catalog_path, output, lock_path):
    source, output = Path(source).resolve(), Path(output).resolve()
    profile, catalog, lock = read_json(profile_path), read_json(catalog_path), read_json(lock_path)
    verify_source(source,lock)
    by_id = {row["id"]:row["definition"] for row in catalog["objects"]}
    for id, footprint in profile["footprints"].items():
        definition=by_id.get(id)
        if not definition or [definition["width"],definition["depth"]] != footprint:
            raise ValidationError(f"Pegada do CRONA mudou: {id}; revisar a receita de arte")
    output.mkdir(parents=True,exist_ok=True)
    assets=output/"client/public/arte/mobiliario"
    env=os.environ.copy(); env.update(ESC="1",AUMENTO="1.2")
    # Cada processo tem seu motor. O exportador gira o motor global e não pode dividir estado com a cena.
    subprocess.run([sys.executable,str(source/profile["renderer"]),*profile["recipes"],"--destino",str(assets)],env=env,check=True)
    textures=output/"client/public/arte/texturas/px/crona_cozy_cozinha"
    subprocess.run([sys.executable,str(source/profile["texture_renderer"]),"crona_cozy_cozinha"],env=env,check=True)
    shutil.copytree(source/"client/public/arte/texturas/px/crona_cozy_cozinha",textures,dirs_exist_ok=True)
    previews=output/"previews";previews.mkdir(exist_ok=True)
    subprocess.run([sys.executable,str(source/profile["room_renderer"]),str(previews/"cozinha.png"),"0"],env=env,check=True)
    skins=read_json(assets/"moveis.json")
    report=audit_skins(catalog,skins,assets)
    report.update(profile=profile["id"],name=profile["name"],source_commit=profile["source_commit"])
    report["catalog_source_sha256"] = catalog["source_sha256"]
    ready={r["id"]:r["skin"] for r in report["objects"] if r["status"]=="ready"}
    write_json(output/"moveis.patch.json",ready)
    write_json(output/"texturas.patch.json",{"cozinha_fazenda":{"px":"crona_cozy_cozinha"}})
    original_textures=read_json(source/"client/public/arte/texturas/texturas.json")
    write_json(output/"texturas.merged.json",original_textures | {"cozinha_fazenda":{"px":"crona_cozy_cozinha"}})
    # Conserva campos que o mapa tático já usa; não remove outros modelos do jogo.
    original=read_json(source/"client/public/arte/mobiliario/moveis.json")
    write_json(output/"moveis.merged.json",merge_manifest(original,ready))
    write_json(output/"skins.json",report)
    write_json(output/"requests.json",{"profile":profile["id"],"objects":[r for r in report["objects"] if r["status"]!="ready"]})
    render_gallery(report,output/"index.html")
    return report
