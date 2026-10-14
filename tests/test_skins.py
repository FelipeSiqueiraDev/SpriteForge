import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from spriteforge.core import ValidationError
from spriteforge.skins import audit_skins, merge_manifest, resolve_skin, verify_source


class SkinContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        Image.new('RGBA', (16,16), (100,80,60,180)).save(self.root/'piece.png')
        self.definition = dict(id='stove',name='Fogão',category='kitchen',width=2,depth=1,
                               height=0.5,states=2,rotations=[0,2,4,6],walkable=False)
        self.catalog = dict(version=1,objects=[dict(id='stove',name='Fogão',type='floor',definition=self.definition)])
        views = {str(r): dict(arquivo='piece.png',ax=8,ay=15) for r in [0,2,4,6]}
        self.skin = dict(pixel=True,exato=True,escala=1,real=[1.5,0.75,1.4],giros=views,
                         estados={'1':dict(giros=copy.deepcopy(views))})

    def test_missing_skin_keeps_object_and_procedural_fallback(self):
        before=copy.deepcopy(self.catalog)
        report=audit_skins(self.catalog,{},self.root)
        self.assertEqual(report['summary'],dict(ready=0,partial=0,pending=1))
        self.assertEqual(report['objects'][0]['definition'],self.definition)
        self.assertEqual(self.catalog,before)
        self.assertIsNone(resolve_skin(self.definition,None,0))

    def test_requires_each_rotation_and_state(self):
        del self.skin['estados']['1']['giros']['4']
        report=audit_skins(self.catalog,{'stove':self.skin},self.root)
        self.assertEqual(report['objects'][0]['missing_views'],['estado 1, giro 4'])
        self.assertIsNone(report['objects'][0]['skin'])
        self.assertIsNone(resolve_skin(self.definition,self.skin,4,1))
        self.assertIsNone(resolve_skin(self.definition,self.skin,4,2))

    def test_physical_art_height_is_not_seat_height(self):
        report=audit_skins(self.catalog,{'stove':self.skin},self.root)
        self.assertEqual(report['summary']['ready'],1)
        self.assertEqual(self.definition['height'],0.5)

    def test_rejects_scaled_skin_and_invalid_physical_dimension(self):
        for field,value in [('escala',2),('pixel',False),('real',[1,1,float('inf')])]:
            with self.subTest(field=field):
                skin=copy.deepcopy(self.skin);skin[field]=value
                with self.assertRaises(ValidationError):audit_skins(self.catalog,{'stove':skin},self.root)

    def test_rejects_missing_and_outside_images(self):
        for filename in ['missing.png','../outside.png']:
            skin=copy.deepcopy(self.skin);skin['giros']['0']['arquivo']=filename
            with self.subTest(filename=filename),self.assertRaises(ValidationError):
                audit_skins(self.catalog,{'stove':skin},self.root)

    def test_rejects_unknown_object_and_invalid_anchor(self):
        with self.assertRaises(ValidationError):audit_skins(self.catalog,{'new':self.skin},self.root)
        self.skin['giros']['0']['ax']=float('nan')
        with self.assertRaises(ValidationError):audit_skins(self.catalog,{'stove':self.skin},self.root)

    def test_preserves_other_objects_and_tactical_views(self):
        original={'other':{'giros':{}},'stove':{'cima':{'arquivo':'top.png'},'cimaEstados':{},
                                              'encosta':True,'chamas':{'0':[[1,2,3]]}}}
        before=copy.deepcopy(original)
        merged=merge_manifest(original,{'stove':self.skin})
        self.assertEqual(merged['other'],original['other'])
        self.assertEqual(merged['stove']['cima'],original['stove']['cima'])
        self.assertTrue(merged['stove']['encosta'])
        self.assertNotIn('chamas',merged['stove'])
        self.assertEqual(original,before)

    def test_renderer_changes_require_review(self):
        source=self.root/'render.py';source.write_text('print(1)\n')
        lock={'files':{'render.py':hashlib.sha256(b'print(1)').hexdigest()}}
        verify_source(self.root,lock)
        source.write_text('print(2)\n')
        with self.assertRaises(ValidationError):verify_source(self.root,lock)


if __name__=='__main__':unittest.main()
