import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from spriteforge.core import Bundle, DIRECTIONS
from spriteforge.crona import (CELL, PIVOT, ENGINE_TO_SHEET, ENGINE_VECTORS,
    LEGACY_PERSON_SCALE, METRES_PER_MODEL_UNIT, METRES_PER_TILE,
    VERTICAL_PX_PER_METRE, export_crona, iso, model_to_map, project_model, rotate_local)
from spriteforge.rig import pose, render


class CronaTests(unittest.TestCase):
    def test_native_floor_is_64_by_32(self):
        points = [iso(0, 0), iso(1, 0), iso(1, 1), iso(0, 1)]
        self.assertEqual([p.tolist() for p in points], [[0, 0], [32, 16], [0, 32], [-32, 16]])
        self.assertEqual(iso(0, 0, 1).tolist(), [0, -32])

    def test_all_headings_match_crona_engine_direction_after_projection(self):
        for engine, (dx, dy) in enumerate(ENGINE_VECTORS):
            expected = iso(dx, dy)
            facing = rotate_local([0, 1, 0], ENGINE_TO_SHEET[engine])
            actual = project_model(facing, origin=(0, 0))
            expected /= np.linalg.norm(expected)
            actual /= np.linalg.norm(actual)
            np.testing.assert_allclose(actual, expected, atol=1e-12)
        self.assertEqual(ENGINE_TO_SHEET[0], 'NE')
        self.assertEqual(ENGINE_TO_SHEET[7], 'N')

    def test_camera_has_exact_two_to_one_ground_ratio_without_squeezing_body(self):
        origin = project_model([0, 0, 0], origin=(0, 0))
        horizontal = project_model([1, 0, 0], origin=(0, 0))-origin
        ground_depth = project_model([0, 1, 0], origin=(0, 0))-origin
        vertical = project_model([0, 0, 1], origin=(0, 0))-origin
        self.assertAlmostEqual(horizontal[0]/ground_depth[1], 2)
        self.assertAlmostEqual(-vertical[1]/horizontal[0], math.cos(math.pi/6))
        self.assertAlmostEqual(-vertical[1]/METRES_PER_MODEL_UNIT, VERTICAL_PX_PER_METRE)

    def test_projection_matches_game_formula_for_many_world_points(self):
        points = np.random.default_rng(123).normal(size=(100, 3))*30
        world = model_to_map(points)
        reference = np.stack(((world[:,0]-world[:,1])*32,
                              (world[:,0]+world[:,1])*16-world[:,2]*32), axis=-1)+PIVOT
        np.testing.assert_allclose(project_model(points), reference, atol=1e-10)

    def test_crona_export_preserves_pixels_and_has_matching_feet_and_scale(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            recipe = json.loads(Path('templates/humanoid/base.json').read_text())
            idle, _, _ = render(recipe, 'S', 'idle', 0)
            walk, _, _ = render(recipe, 'S', 'walk', 0)
            images = {(action, direction): [frame.copy()] for action, frame in (('idle', idle), ('walk', walk)) for direction in DIRECTIONS}
            # Fixture pequena verifica o formato/contrato; poses reais continuam registradas por direção.
            poses = {f'{action}/{direction}/00': pose(action, 0) for action in ('idle', 'walk') for direction in DIRECTIONS}
            rig = {'profile':'crona-iso-v1', 'stride_world_units_per_loop':22, 'poses':poses}
            (root/'rig.json').write_text(json.dumps(rig))
            bundle = Bundle({'id':'fixture','cell':list(CELL),'pivot':list(PIVOT),
                             'animations':{'idle':{'duration_ms':200},'walk':{'duration_ms':100}}}, images, {}, root)
            out=root/'crona'
            export_crona(bundle,out)
            data=json.loads((out/'anim.json').read_text())
            self.assertEqual(data['versao'],2)
            self.assertAlmostEqual(data['escala']*LEGACY_PERSON_SCALE,1)
            self.assertEqual(set(data['estados']['desarmado']), {d.lower() for d in DIRECTIONS})
            for direction in DIRECTIONS:
                for action,name in (('idle','parado'),('walk','andar')):
                    clip=data['estados']['desarmado'][direction.lower()][name]
                    with Image.open(out/clip['arquivo']) as strip:
                        self.assertEqual(strip.size,CELL)
                        self.assertEqual(strip.tobytes(),images[action,direction][0].tobytes())
                    self.assertEqual([clip['ax'],clip['ay']],list(PIVOT))
                    self.assertEqual(len(clip['pes']),clip['quadros'])
                    self.assertEqual(len(clip['pes'][0]),2)
            c=data['estados']['desarmado']['s']['andar']
            self.assertAlmostEqual(c['casasPorCiclo']*LEGACY_PERSON_SCALE,22*METRES_PER_MODEL_UNIT/METRES_PER_TILE)


if __name__=='__main__':
    unittest.main()
