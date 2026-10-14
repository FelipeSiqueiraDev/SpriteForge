"""Contact sheet das peças exportadas; amplia apenas por múltiplos inteiros."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser=argparse.ArgumentParser()
parser.add_argument('--assets',type=Path,default=Path('dist/skins/crona-cozy-v1/client/public/arte/mobiliario'))
parser.add_argument('--output',type=Path,default=Path('previews/cozinha-skins-moveis.png'))
args=parser.parse_args()
skins=json.loads((args.assets/'moveis.json').read_text(encoding='utf-8'))
canvas=Image.new('RGB',(840,300*((len(skins)+2)//3)),'#d0d0c7')
font=ImageFont.load_default(size=14)
for i,(id,skin) in enumerate(skins.items()):
    x=(i%3)*280;y=(i//3)*300
    image=Image.open(args.assets/skin['giros']['4']['arquivo']).convert('RGBA')
    scale=max(1,min(2,252//image.width,260//image.height))
    image=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
    canvas.paste(image,(x+(280-image.width)//2,y+260-image.height),image)
    ImageDraw.Draw(canvas).text((x+14,y+277),id,fill='#263a40',font=font)
args.output.parent.mkdir(parents=True,exist_ok=True)
canvas.save(args.output)
