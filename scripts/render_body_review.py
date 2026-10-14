"""Compara o corpo-base v1 do histórico com os frames atuais na mesma câmera."""
import argparse
import importlib.util
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser=argparse.ArgumentParser()
parser.add_argument('--baseline-source',type=Path,required=True)
parser.add_argument('--baseline-recipe',type=Path,required=True)
parser.add_argument('--input',type=Path,default=Path('demo-input'))
parser.add_argument('--output',type=Path,default=Path('previews/humanoid-before-after.png'))
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('spriteforge._baseline_rig',args.baseline_source)
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
recipe=json.loads(args.baseline_recipe.read_text(encoding='utf-8'))
canvas=Image.new('RGB',(960,600),'#d0d0c7')
draw=ImageDraw.Draw(canvas);font=ImageFont.load_default(size=16)
for n,direction in enumerate(('S','SE','E')):
    before,_,_=baseline.render(recipe,direction,'idle',0)
    with Image.open(args.input/'humanoid-base/frames/idle'/direction/'00.png') as source:
        after=source.convert('RGBA')
    for row,image in enumerate((before,after)):
        x=n*320+32;y=row*300+40
        image=image.resize((256,256),Image.Resampling.NEAREST)
        canvas.paste(image,(x,y),image)
        draw.text((n*320+16,row*300+12),('ANTERIOR' if row==0 else 'CORPO REFINADO')+' / '+direction,fill='#403b33',font=font)
args.output.parent.mkdir(parents=True,exist_ok=True)
canvas.save(args.output)
