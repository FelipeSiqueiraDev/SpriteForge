"""Package generated drawings into a review loop; never redraw or warp them.

The source is a 3x2 sheet made with imagegen from the approved character.
Registration uses the scalp and applies translation only. The 128px copies
are uniformly scaled studies, not calibrated CRONA production exports.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def assemble(source: Path, output: Path):
    image = Image.open(source).convert('RGBA')
    width, height = image.size
    if width % 3 or height % 2 or width // 3 != height // 2:
        raise ValueError('Expected a 3x2 sheet of equal square cells')
    cell = width // 3
    output.mkdir(parents=True, exist_ok=True)
    (output / 'frames').mkdir(exist_ok=True)
    (output / 'frames-128').mkdir(exist_ok=True)
    frames, previews, records = [], [], []
    # Contact + passing for each leg. The two other generated drawings repeat
    # their respective contact poses rather than adding useful walk phases.
    source_indices = (0, 1, 3, 4)
    for index, source_index in enumerate(source_indices):
        x, y = source_index % 3 * cell, source_index // 3 * cell
        frame = image.crop((x, y, x + cell, y + cell))
        pixels = np.asarray(frame)
        r, g, b, a = [pixels[:, :, c].astype(float) for c in range(4)]
        scalp = (a > 200) & (r > 135) & (r > g * 1.1) & (g > b * 1.05)
        scalp[int(cell * .32):] = False
        yy, xx = np.where(scalp)
        if len(xx) < cell:
            raise ValueError(f'Cannot register head in frame {index}')
        head_x = (int(xx.min()) + int(xx.max())) / 2
        head_y = int(yy.min())
        bob = (0, 3, 0, 3)[index]
        dx, dy = round(cell / 2 - head_x), round(cell * .045 + bob - head_y)
        aligned = Image.new('RGBA', (cell, cell))
        aligned.alpha_composite(frame, (dx, dy))
        # Ensure rigid registration did not clip any visible source pixels.
        original_count = int((a > 127).sum())
        aligned_count = int((np.asarray(aligned)[:, :, 3] > 127).sum())
        if aligned_count != original_count:
            raise ValueError(f'Registration clipped frame {index}')
        aligned.save(output / 'frames' / f'{index:02d}.png')
        frames.append(aligned)
        preview = Image.new('RGBA', aligned.size, '#283340')
        preview.alpha_composite(aligned)
        previews.append(preview.convert('RGB'))
        # Same scale in x and y: no flattening of heads or stretching of legs.
        scaled_size = round(cell * .2)
        small = aligned.resize((scaled_size, scaled_size), Image.Resampling.NEAREST)
        native = Image.new('RGBA', (128, 128))
        native.alpha_composite(small, (64 - scaled_size // 2, 112 - round(cell * .94 * scaled_size / cell)))
        native.save(output / 'frames-128' / f'{index:02d}.png')
        records.append({'frame': index, 'source_index': source_index, 'source_cell': [x, y, cell, cell],
                        'translation': [dx, dy], 'visible_pixels_preserved': original_count})
    previews[0].save(output / 'carequinha-caminhada.gif', save_all=True,
                     append_images=previews[1:], duration=180, loop=0, disposal=2)
    frames[0].save(output / 'carequinha-caminhada.png', save_all=True,
                   append_images=frames[1:], duration=180, loop=0, disposal=1, blend=0)
    review = Image.new('RGB', (cell * 2, cell * 2), '#283340')
    draw = ImageDraw.Draw(review)
    for index, preview in enumerate(previews):
        x, y = index % 2 * cell, index // 2 * cell
        review.paste(preview, (x, y))
        draw.text((x + 12, y + 12), str(index + 1), fill='#ffffff')
    review.save(output / 'carequinha-quadros.png')
    (output / 'registration.json').write_text(json.dumps({
        'source': source.name, 'source_size': list(image.size), 'cell': cell,
        'duration_ms': 180, 'frame_count': len(frames), 'direction': 'three-quarter-front-right',
        'status': 'visual-study-not-crona-calibrated', 'registration': 'translation-only',
        'records': records,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    assemble(args.source, args.output)
