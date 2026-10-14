import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from spriteforge.cli import main
from spriteforge.core import DIRECTIONS, ValidationError, export_bundle, load_bundle
from spriteforge.demo import generate_demo


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = generate_demo(self.root / "input")
        self.spec = json.loads(self.manifest.read_text())

    def save(self):
        self.manifest.write_text(json.dumps(self.spec), encoding="utf-8")

    def first_frame(self):
        return self.manifest.parent / self.spec["animations"]["walk"]["directions"]["S"][0]

    def test_export_roundtrip_preserves_every_pixel_and_atlas_order(self):
        bundle = load_bundle(self.manifest)
        out = self.root / "output"
        export_bundle(bundle, out)
        atlas = json.loads((out / "atlas.json").read_text())
        self.assertEqual(atlas["direction_order"], list(DIRECTIONS))
        self.assertEqual(bundle.report["frame_count"], 80)
        for action, clip in self.spec["animations"].items():
            with Image.open(out / f"{action}.png") as sheet:
                self.assertEqual(sheet.size, (96 * clip["frame_count"], 96 * 8))
                for row, direction in enumerate(DIRECTIONS):
                    for col, original in enumerate(bundle.images[action, direction]):
                        box = atlas["animations"][action]["directions"][direction][col]
                        crop = sheet.crop((box["x"], box["y"], box["x"] + box["w"], box["y"] + box["h"]))
                        self.assertEqual(crop.tobytes(), original.tobytes())
                        with Image.open(out / "frames" / action / direction / f"{col:02d}.png") as individual:
                            self.assertEqual(individual.tobytes(), original.tobytes())
                        self.assertEqual(box["pivot"], [48, 80])
        self.assertTrue((out / "index.html").exists())

    def test_gif_has_loop_and_duration_without_trails(self):
        bundle = load_bundle(self.manifest)
        out = self.root / "output"
        export_bundle(bundle, out)
        with Image.open(out / "walk-S.gif") as gif:
            self.assertEqual(gif.n_frames, 6)
            self.assertEqual(gif.info["loop"], 0)
            for index in range(6):
                gif.seek(index)
                self.assertEqual(gif.info["duration"], 100)
                self.assertEqual(gif.disposal_method, 2)

    def test_missing_direction_fails(self):
        del self.spec["animations"]["walk"]["directions"]["NE"]
        self.save()
        with self.assertRaisesRegex(ValidationError, "oito direções"):
            load_bundle(self.manifest)

    def test_incorrect_frame_count_fails(self):
        self.spec["animations"]["walk"]["directions"]["N"].pop()
        self.save()
        with self.assertRaisesRegex(ValidationError, "esperados 6"):
            load_bundle(self.manifest)

    def test_missing_file_fails(self):
        self.first_frame().unlink()
        with self.assertRaisesRegex(ValidationError, "não foi possível abrir"):
            load_bundle(self.manifest)

    def test_wrong_cell_size_fails(self):
        Image.new("RGBA", (80, 80)).save(self.first_frame())
        with self.assertRaisesRegex(ValidationError, "96×96"):
            load_bundle(self.manifest)

    def test_border_pixel_fails_instead_of_silently_cropping(self):
        with Image.open(self.first_frame()) as image:
            image.putpixel((0, 50), (255, 0, 0, 255))
            image.save(self.first_frame())
        with self.assertRaisesRegex(ValidationError, "borda"):
            load_bundle(self.manifest)

    def test_empty_or_partial_alpha_frame_fails(self):
        Image.new("RGBA", (96, 96)).save(self.first_frame())
        with self.assertRaisesRegex(ValidationError, "vazio"):
            load_bundle(self.manifest)
        image = Image.new("RGBA", (96, 96))
        image.putpixel((48, 50), (255, 0, 0, 128))
        image.save(self.first_frame())
        with self.assertRaisesRegex(ValidationError, "alpha parcial"):
            load_bundle(self.manifest)

    def test_path_escape_is_rejected(self):
        self.spec["animations"]["walk"]["directions"]["S"][0] = "../../outside.png"
        self.save()
        with self.assertRaisesRegex(ValidationError, "dentro da pasta"):
            load_bundle(self.manifest)

    def test_invalid_manifest_returns_nonzero_without_traceback(self):
        self.manifest.write_text("{broken")
        with contextlib.redirect_stderr(io.StringIO()) as capture:
            status = main(["validate", str(self.manifest)])
        self.assertEqual(status, 1)
        self.assertIn("manifesto", capture.getvalue())

    def test_preview_title_cannot_inject_html(self):
        self.spec["name"] = '<script>alert("unsafe")</script>'
        self.save()
        bundle = load_bundle(self.manifest)
        out = self.root / "output"
        export_bundle(bundle, out)
        content = (out / "index.html").read_text()
        self.assertNotIn('<script>alert("unsafe")</script>', content)
        self.assertIn("&lt;script&gt;", content)

    def test_source_and_output_cannot_overlap(self):
        with contextlib.redirect_stderr(io.StringIO()):
            status = main(["build", str(self.manifest), "--output", str(self.manifest.parent.parent)])
        self.assertEqual(status, 1)


if __name__ == "__main__":
    unittest.main()
