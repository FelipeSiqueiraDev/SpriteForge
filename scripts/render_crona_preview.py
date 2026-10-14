"""Prévia dos sprites sobre o piso real do CRONA, em pixel 1:1.

Só produz imagens de conferência; não altera nem inicia o jogo.
"""

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

from spriteforge.core import DIRECTIONS
from spriteforge.crona import ENGINE_TO_SHEET, PIVOT, SHEET_TO_WORLD, iso

TILE = Path('integrations/crona/floor-tile.png')


def panel(direction, frame, tile):
    image = Image.new('RGB', (256, 256), '#14252c')
    draw = ImageDraw.Draw(image)
    anchor = (128, 160)
    for x,y in sorted(((x,y) for x in range(3) for y in range(3)), key=lambda p:sum(p)):
        p=iso(x-1.5,y-1.5)
        image.paste(tile,(round(anchor[0]+p[0]-32),round(anchor[1]+p[1])),tile)
    draw.ellipse((anchor[0]-16,anchor[1]-5,anchor[0]+16,anchor[1]+5),fill='#55544a')
    image.paste(frame,(anchor[0]-PIVOT[0],anchor[1]-PIVOT[1]),frame)
    engine=ENGINE_TO_SHEET.index(direction)
    draw.text((12,12),f'TELA {direction}  |  CRONA {engine}',fill='#f0c461')
    draw.text((12,30),'PISO 64x32  |  CAMERA 30 graus',fill='#afc3c7')
    dx,dy=SHEET_TO_WORLD[direction]
    delta=iso(dx,dy)
    delta=delta/max(1,float(math.hypot(*delta)))
    # A seta aparece ao lado do pé para indicar a mesma direção sem cobrir o corpo.
    start=(anchor[0]+48,anchor[1]+35)
    end=(round(start[0]+delta[0]*25),round(start[1]+delta[1]*25))
    draw.line((start,end),fill='#60d7c7',width=2)
    cross=(-delta[1],delta[0])
    back=(end[0]-delta[0]*7,end[1]-delta[1]*7)
    draw.polygon([end,(round(back[0]+cross[0]*4),round(back[1]+cross[1]*4)),
                  (round(back[0]-cross[0]*4),round(back[1]-cross[1]*4))],fill='#60d7c7')
    return image


def generate(input_dir, output):
    output.mkdir(parents=True,exist_ok=True)
    with Image.open(TILE) as source:
        tile=source.convert('RGBA')
    frames=input_dir/'humanoid-base'/'frames'
    standing=Image.new('RGB',(1024,512),'#14252c')
    for n,direction in enumerate(DIRECTIONS):
        with Image.open(frames/'idle'/direction/'00.png') as source:
            standing.paste(panel(direction,source.convert('RGBA'),tile),(n%4*256,n//4*256))
    standing.save(output/'crona-isometric.png')
    walk=[]
    for index in range(6):
        image=Image.new('RGB',(1024,512),'#14252c')
        for n,direction in enumerate(DIRECTIONS):
            with Image.open(frames/'walk'/direction/f'{index:02d}.png') as source:
                image.paste(panel(direction,source.convert('RGBA'),tile),(n%4*256,n//4*256))
        walk.append(image)
    walk[0].save(output/'crona-walk.gif',save_all=True,append_images=walk[1:],duration=100,loop=0,disposal=2,optimize=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('demo-input'))
    parser.add_argument('--output',type=Path,default=Path('previews'))
    args=parser.parse_args()
    generate(args.input,args.output)
