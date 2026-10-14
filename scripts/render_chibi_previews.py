"""Reproducible review images for the animated chibi study."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from spriteforge.core import DIRECTIONS
from render_crona_preview import panel


def sprite(root,variant,action,direction,index):
    with Image.open(root/variant/'frames'/action/direction/f'{index:02d}.png') as source:
        return source.convert('RGBA')


def paste(canvas,image,point,scale=2):
    image=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
    canvas.paste(image,point,image)


def generate(root,output):
    output.mkdir(parents=True,exist_ok=True)
    font=ImageFont.load_default(size=15)
    standing=Image.new('RGB',(1024,568),'#14252c');draw=ImageDraw.Draw(standing)
    for n,direction in enumerate(DIRECTIONS):
        x,y=n%4*256,n//4*284
        draw.text((x+12,y+8),direction,fill='#f0c461',font=font)
        paste(standing,sprite(root,'chibi-base','idle',direction,0),(x,y+28))
    standing.save(output/'chibi-base.png')
    walk=[];modular=[];board=[]
    with Image.open('integrations/crona/floor-tile.png') as source:
        tile=source.convert('RGBA')
    for index in range(6):
        frame=Image.new('RGB',(1024,568),'#14252c');draw=ImageDraw.Draw(frame)
        comparison=Image.new('RGB',(1024,1120),'#14252c');compare_draw=ImageDraw.Draw(comparison)
        on_board=Image.new('RGB',(1024,512),'#14252c')
        for n,direction in enumerate(DIRECTIONS):
            image=sprite(root,'chibi-base','walk',direction,index)
            x,y=n%4*256,n//4*284
            draw.text((x+12,y+8),direction,fill='#f0c461',font=font)
            paste(frame,image,(x,y+28))
            x,y=n%2*512,n//2*280
            compare_draw.text((x+12,y+5),direction+' / BASE             PECAS DE TESTE',fill='#f0c461',font=font)
            paste(comparison,image,(x,y+24))
            paste(comparison,sprite(root,'chibi-outfit-demo','walk',direction,index),(x+256,y+24))
            on_board.paste(panel(direction,image,tile),(n%4*256,n//4*256))
        walk.append(frame);modular.append(comparison);board.append(on_board)
    for filename,frames in (('chibi-walk.gif',walk),('chibi-modular.gif',modular),('chibi-crona-walk.gif',board)):
        frames[0].save(output/filename,save_all=True,append_images=frames[1:],duration=100,loop=0,disposal=2,optimize=False)
    board[0].save(output/'chibi-crona.png')
    strip=Image.new('RGB',(1536,288),'#14252c');draw=ImageDraw.Draw(strip)
    for index in range(6):
        draw.text((index*256+12,7),f'SE / {index+1}',fill='#f0c461',font=font)
        paste(strip,sprite(root,'chibi-base','walk','SE',index),(index*256,30))
    strip.save(output/'chibi-walk-SE.png')
    comparison=Image.new('RGB',(1024,640),'#14252c');draw=ImageDraw.Draw(comparison)
    for n,direction in enumerate(('S','SE','E','N')):
        for row,variant,label in ((0,'humanoid-base','V2 / anterior'),(1,'chibi-base','V3 / chibi animado')):
            draw.text((n*256+12,row*320+12),label+' / '+direction,fill='#f0c461',font=font)
            paste(comparison,sprite(root,variant,'idle',direction,0),(n*256,row*320+45))
    comparison.save(output/'chibi-before-after.png')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('demo-input'))
    parser.add_argument('--output',type=Path,default=Path('previews'))
    args=parser.parse_args();generate(args.input,args.output)
