import json
import unittest
from pathlib import Path
import numpy as np
from spriteforge.chibi import ARM_LENGTH, LEG_LENGTH, STRIDE, build_scene, head, patch, pose
from spriteforge.core import DIRECTIONS, ValidationError
from spriteforge.rig import Scene, render, rasterize, validate_recipe


class ChibiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=json.loads(Path('templates/humanoid/chibi-base.json').read_text(encoding='utf-8'))
        cls.dressed=json.loads(Path('templates/humanoid/chibi-outfit-demo.json').read_text(encoding='utf-8'))

    def test_bones_keep_their_lengths_through_the_complete_cycle(self):
        for action,count in (('idle',4),('walk',6)):
            for index in range(count):
                joints=pose(action,index)['joints']
                for side in ('left','right'):
                    for chain,length in ((('hip','knee','ankle'),LEG_LENGTH),(('shoulder','elbow','wrist'),ARM_LENGTH)):
                        a,b,c=[np.asarray(joints[side+'_'+j]) for j in chain]
                        self.assertAlmostEqual(np.linalg.norm(b-a),length,places=9)
                        self.assertAlmostEqual(np.linalg.norm(c-b),length,places=9)

    def test_planted_feet_stay_at_the_same_world_position_as_root_moves(self):
        # Include frame 0 of the next cycle to verify the loop boundary too.
        for side,indices in (('left',range(4)),('right',range(3,7))):
            world=[]
            for index in indices:
                current=pose('walk',index%6)
                self.assertTrue(current['contacts'][side])
                foot=current['feet'][side]
                self.assertAlmostEqual(foot[2],0,places=9)
                world.append(foot[1]+STRIDE*index/6)
            np.testing.assert_allclose(world,[world[0]]*len(world),atol=1e-10)

    def test_swing_leg_lifts_and_opposite_arm_goes_forward(self):
        first=pose('walk',0)
        for side in ('left','right'):
            j=first['joints']
            self.assertLess(j[side+'_wrist'][1]*j[side+'_ankle'][1],0)
        self.assertFalse(pose('walk',1)['contacts']['right'])
        self.assertGreater(pose('walk',1)['feet']['right'][2],0)
        self.assertFalse(pose('walk',4)['contacts']['left'])

    def test_appearance_uses_identical_joints_and_changes_the_render(self):
        for direction in ('S','SE','N'):
            base,_,p1=render(self.base,direction,'walk',1)
            dressed,_,p2=render(self.dressed,direction,'walk',1)
            self.assertEqual(p1,p2)
            self.assertNotEqual(base.tobytes(),dressed.tobytes())

    def test_shaped_head_hides_front_facial_decals_when_viewed_from_back(self):
        scene=Scene();head(scene,'#e8ac83',0)
        patch(scene,0,49,7,5,'#ff00ff',0,.6)
        front,_=rasterize(scene,'S');back,_=rasterize(scene,'N')
        def magenta(image):
            a=np.asarray(image)
            return np.count_nonzero((a[:,:,0]>100)&(a[:,:,2]>100)&(a[:,:,1]<30)&(a[:,:,3]>0))
        self.assertGreater(magenta(front),0)
        self.assertEqual(magenta(back),0)

    def test_every_direction_has_binary_alpha_and_safe_margins(self):
        for recipe in (self.base,self.dressed):
            for direction in DIRECTIONS:
                image,_,_=render(recipe,direction,'walk',1)
                alpha=image.getchannel('A')
                self.assertEqual(set(alpha.get_flattened_data()),{0,255})
                x0,y0,x1,y1=alpha.getbbox()
                self.assertGreater(min(x0,y0),0)
                self.assertLess(max(x1,y1),128)

    def test_neutral_height_and_removable_outfit(self):
        recipe=self.base|{'outfit':None,'hair':None}
        scene=build_scene(recipe,pose('idle',0))
        self.assertEqual({part for _,_,part in scene.triangles},{'body'})
        self.assertAlmostEqual(max(p[2] for v,_,_ in scene.triangles for p in v),63.5)

    def test_unknown_body_model_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_recipe(self.base|{'model':'unknown'})
