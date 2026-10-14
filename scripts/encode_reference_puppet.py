"""Encode the browser-rendered PNGs, preserving the supplied animation art."""
import argparse
import json
from pathlib import Path
from PIL import Image


def encode(root):
    meta=json.loads((root/'rig.json').read_text(encoding='utf-8'))
    count,duration=meta['frame_count'],meta['duration_ms']
    rgba=[Image.open(root/'frames'/f'{i:02d}.png').convert('RGBA') for i in range(count)]
    opaque=[Image.open(root/'preview-frames'/f'{i:02d}.png').convert('RGB') for i in range(count)]
    palette=opaque[0].quantize(colors=256,dither=Image.Dither.NONE)
    gif=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in opaque]
    gif[0].save(root/'carequinha-caminhada.gif',save_all=True,append_images=gif[1:],duration=duration,loop=0,disposal=2,optimize=False)
    rgba[0].save(root/'carequinha-caminhada.png',save_all=True,append_images=rgba[1:],duration=duration,loop=0,disposal=1,blend=0)
    apng=Image.open(root/'carequinha-caminhada.png')
    decoded_gif=Image.open(root/'carequinha-caminhada.gif')
    assert apng.n_frames==decoded_gif.n_frames==count
    head=[]
    for i in range(count):
        apng.seek(i);decoded_gif.seek(i)
        assert apng.convert('RGBA').tobytes()==rgba[i].tobytes()
        assert decoded_gif.info['duration']==duration
        bob=round(meta['poses'][i]['bob'])
        head.append(decoded_gif.convert('RGB').crop((180,18+bob,333,158+bob)).tobytes())
    assert len(set(head))==1,'GIF encoding changed the registered head across frames'
    report=json.loads((root/'validation.json').read_text(encoding='utf-8'))
    report.update(apng_pixel_roundtrip='passed',gif_head_consistency='passed',encoded_frame_count=count)
    (root/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'{count} frames encoded; APNG pixels and GIF head consistency passed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input',type=Path)
    encode(parser.parse_args().input)
