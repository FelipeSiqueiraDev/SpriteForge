from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import ValidationError, export_bundle, load_bundle, write_wardrobe


def main(argv=None):
    parser = argparse.ArgumentParser(description="SpriteForge — validação e exportação de sprites")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Gera um boneco técnico; não é um personagem aprovado")
    demo.add_argument("--output", type=Path, default=Path("demo-input"))
    rig = commands.add_parser("rig", help="Renderiza o corpo-base articulado com uma receita de aparência")
    rig.add_argument("recipe", type=Path)
    rig.add_argument("--output", type=Path, default=Path("demo-input"))
    rig.add_argument("--workers", type=int, default=1, help="Processos de renderização, de 1 a 8")
    wardrobe = commands.add_parser("wardrobe", help="Compara aparências já exportadas no mesmo visualizador")
    wardrobe.add_argument("directories", type=Path, nargs="+")
    wardrobe.add_argument("--output", type=Path, default=Path("dist/wardrobe.html"))
    crona = commands.add_parser("crona", help="Exporta tiras e anim.json no formato do tabuleiro CRONA")
    crona.add_argument("manifest", type=Path)
    crona.add_argument("--output", type=Path, default=Path("dist/crona"))
    skins = commands.add_parser("skins", help="Produz skins de móveis a partir do renderizador do CRONA")
    skins.add_argument("--source", type=Path, required=True)
    skins.add_argument("--profile", type=Path, default=Path("skins/profiles/crona-cozy-v1.json"))
    skins.add_argument("--catalog", type=Path, default=Path("integrations/crona/catalog.json"))
    skins.add_argument("--lock", type=Path, default=Path("integrations/crona/skin-source-lock.json"))
    skins.add_argument("--output", type=Path, default=Path("dist/skins/crona-cozy-v1"))
    for name in ("validate", "build"):
        command = commands.add_parser(name)
        command.add_argument("manifest", type=Path)
        if name == "build":
            command.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    try:
        if args.command == "skins":
            from .skins import build_skins
            report = build_skins(args.source,args.profile,args.catalog,args.output,args.lock)
            print(json.dumps(report["summary"],ensure_ascii=False,indent=2))
        elif args.command == "crona":
            from .crona import export_crona
            bundle = load_bundle(args.manifest)
            export_crona(bundle, args.output / bundle.spec["id"] / "tabuleiro-3d")
            print(args.output / bundle.spec["id"] / "tabuleiro-3d")
        elif args.command == "wardrobe":
            write_wardrobe(args.directories, args.output)
            print(args.output)
        elif args.command == "rig":
            from .rig import generate_rig
            print(generate_rig(args.recipe, args.output, args.workers))
        elif args.command == "demo":
            from .demo import generate_demo
            print(generate_demo(args.output))
        else:
            bundle = load_bundle(args.manifest)
            if args.command == "build":
                output = args.output / bundle.spec["id"]
                # Impede que um build sobrescreva seus próprios PNGs de origem.
                source_root = args.manifest.resolve().parent
                resolved_output = output.resolve()
                if resolved_output.is_relative_to(source_root) or source_root.is_relative_to(resolved_output):
                    raise ValidationError("Use pastas separadas para origem e saída")
                export_bundle(bundle, output)
                print(f"Exportado: {output}")
            print(json.dumps({"frames": bundle.report["frame_count"], "warnings": bundle.report["warnings"]},
                             ensure_ascii=False, indent=2))
        return 0
    except (ValidationError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
