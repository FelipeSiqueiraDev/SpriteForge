from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import ValidationError, export_bundle, load_bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description="SpriteForge — validação e exportação de sprites")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Gera um boneco técnico; não é um personagem aprovado")
    demo.add_argument("--output", type=Path, default=Path("demo-input"))
    for name in ("validate", "build"):
        command = commands.add_parser(name)
        command.add_argument("manifest", type=Path)
        if name == "build":
            command.add_argument("--output", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
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
