"""Audit the actual generated packages, including parallel frame ordering."""
import argparse
import json
from pathlib import Path
from PIL import Image
import numpy as np
from spriteforge.core import DIRECTIONS, load_bundle, write_json
from spriteforge.crona import LEGACY_PERSON_SCALE, METRES_PER_MODEL_UNIT, VERTICAL_PX_PER_METRE, project_model, rotate_local
from spriteforge.rig import render


def audit(source,dist,output):
    variants={};poses=None
    for variant in ('chibi-base','chibi-outfit-demo'):
        bundle=load_bundle(source/variant/'manifest.json')
        rig=json.loads((source/variant/'rig.json').read_text(encoding='utf-8'))
        recipe=json.loads((source/variant/'appearance.json').read_text(encoding='utf-8'))
        atlas=json.loads((dist/variant/'atlas.json').read_text(encoding='utf-8'))
        crona_root=dist/'crona'/variant/'tabuleiro-3d'
        anim=json.loads((crona_root/'anim.json').read_text(encoding='utf-8'))
        if poses is None:poses=rig['poses']
        assert poses==rig['poses'],'Aparências mudaram o esqueleto'
        assert anim['versao']==2
        assert abs(anim['escala']*LEGACY_PERSON_SCALE-1)<1e-12
        for action,clip in bundle.spec['animations'].items():
            with Image.open(dist/variant/f'{action}.png') as sheet:
                for row,direction in enumerate(DIRECTIONS):
                    game_clip=anim['estados']['desarmado'][direction.lower()]['parado' if action=='idle' else 'andar']
                    with Image.open(crona_root/game_clip['arquivo']) as strip:
                        for index,original in enumerate(bundle.images[action,direction]):
                            box=atlas['animations'][action]['directions'][direction][index]
                            crop=sheet.crop((box['x'],box['y'],box['x']+box['w'],box['y']+box['h']))
                            assert crop.tobytes()==original.tobytes(),'Folha alterou pixels'
                            crop=strip.crop((index*128,0,(index+1)*128,128))
                            assert crop.tobytes()==original.tobytes(),'Tira CRONA alterou pixels'
                            current=rig['poses'][f'{action}/{direction}/{index:02d}']
                            for side,exported in zip(('left','right'),game_clip['pes'][index]):
                                foot=np.asarray(current['feet'][side])
                                xy=project_model(rotate_local(foot,direction),origin=(0,0))*anim['escala']
                                air=max(0,foot[2])*METRES_PER_MODEL_UNIT*VERTICAL_PX_PER_METRE*anim['escala']
                                np.testing.assert_allclose(exported,[*xy,air],atol=.00051)
        # Re-render selected frames directly to verify association in parallel output.
        for action,direction,index in (('idle','E',0),('walk','SE',3),('walk','NW',5)):
            expected,_,_=render(recipe,direction,action,index)
            assert expected.tobytes()==bundle.images[action,direction][index].tobytes(),'Ordem paralela incorreta'
        variants[variant]={'frames':bundle.report['frame_count'],'warnings':bundle.report['warnings'],
                           'pixel_roundtrip':'passed','crona_contacts':'passed','frame_order':'passed'}
    report={'variants':variants,'total_frames':sum(v['frames'] for v in variants.values()),
            'shared_poses':'passed','live_crona_session_verified':False}
    output.parent.mkdir(parents=True,exist_ok=True);write_json(output,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=Path('demo-input'))
    parser.add_argument('--dist',type=Path,default=Path('dist'))
    parser.add_argument('--output',type=Path,default=Path('dist/chibi-validation.json'))
    args=parser.parse_args();audit(args.source,args.dist,args.output)
