import json
import unittest
from pathlib import Path

import numpy as np

from spriteforge.core import DIRECTIONS, ValidationError
from spriteforge.rig import CELL, PARTS, build_scene, pose, render, validate_recipe


class RigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(Path('templates/humanoid/base.json').read_text())
        cls.dressed = json.loads(Path('templates/humanoid/outfit-demo.json').read_text())

    def test_appearance_changes_pixels_without_changing_pose(self):
        for direction in DIRECTIONS:
            bare, _, bare_pose = render(self.base, direction, 'walk', 1)
            dressed, _, dressed_pose = render(self.dressed, direction, 'walk', 1)
            self.assertEqual(bare_pose, dressed_pose)
            self.assertNotEqual(bare.tobytes(), dressed.tobytes())

    def test_all_views_have_margin_and_binary_alpha(self):
        for recipe in (self.base, self.dressed):
            for direction in DIRECTIONS:
                for index in (0, 1, 3, 4):
                    image, _, _ = render(recipe, direction, 'walk', index)
                    self.assertEqual(image.size, (128, 128))
                    alpha = image.getchannel('A')
                    self.assertEqual(set(alpha.get_flattened_data()), {0, 255})
                    x0, y0, x1, y1 = alpha.getbbox()
                    self.assertGreater(x0, 0); self.assertGreater(y0, 0)
                    self.assertLess(x1, CELL[0]); self.assertLess(y1, CELL[1])

    def test_knee_uses_fixed_lengths_in_every_walk_pose(self):
        for index in range(6):
            joints = pose('walk', index)['joints']
            for side in ('left', 'right'):
                hip, knee, ankle = [np.array(joints[side+'_'+joint]) for joint in ('hip', 'knee', 'ankle')]
                self.assertAlmostEqual(np.linalg.norm(knee-hip), 11.2, places=6)
                self.assertAlmostEqual(np.linalg.norm(ankle-knee), 11.2, places=6)

    def test_opposite_contacts_and_contralateral_arms(self):
        first, half = pose('walk', 0), pose('walk', 3)
        self.assertEqual(first['contacts'], {'right': True, 'left': True})
        self.assertFalse(pose('walk', 1)['contacts']['left'])
        self.assertFalse(pose('walk', 4)['contacts']['right'])
        for side in ('left', 'right'):
            self.assertAlmostEqual(first['joints'][side+'_ankle'][1], -half['joints'][side+'_ankle'][1])
            self.assertLess(first['joints'][side+'_wrist'][1] * first['joints'][side+'_ankle'][1], 0)

    def test_front_accessories_occluded_from_back(self):
        _, front, _ = render(self.dressed, 'S', 'idle', 0)
        _, back, _ = render(self.dressed, 'N', 'idle', 0)
        beard = PARTS.index('beard')+1
        self.assertGreater(np.count_nonzero(front == beard), 0)
        self.assertEqual(np.count_nonzero(back == beard), 0)

    def test_neutral_body_has_no_appearance_parts(self):
        for _, _, part in build_scene(self.base, pose('idle', 0)).triangles:
            self.assertEqual(part, 'body')

    def test_render_is_reproducible(self):
        first, mask1, _ = render(self.dressed, 'SE', 'walk', 2)
        second, mask2, _ = render(self.dressed, 'SE', 'walk', 2)
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertTrue(np.array_equal(mask1, mask2))

    def test_invalid_recipe_is_rejected(self):
        for change in ({'body_color': 'invalid'}, {'hair': True}, {'unknown': 'anything'}, {'outfit': {'cape': '#aabbcc'}}):
            with self.assertRaises(ValidationError):
                validate_recipe(self.base | change)


if __name__ == '__main__':
    unittest.main()
