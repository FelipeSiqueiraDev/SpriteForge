# Câmera e formato do tabuleiro CRONA

Conferência feita no [CRONA, commit f08bea38](https://github.com/FelipeSiqueiraDev/CRONA/tree/f08bea3816fe2af49a98975341b0c6fe4eebf158).

## O que foi confirmado

O motor em [`client/src/render/iso.ts`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/client/src/render/iso.ts) projeta:

```text
screenX = (x - y) × 32
screenY = (x + y) × 16 - z × 32
```

`x` e `y` são casas; `z` usa unidades de altura. O chão é um losango 64×32, com os eixos a ±26,565° na imagem. A elevação física da câmera é **30°**; são medidas diferentes. A câmera de 30° do corpo-base anterior já era compatível.

[`shared/src/constants.ts`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/shared/src/constants.ts) define 0,75 m por casa e aproximadamente 52,26 pixels por metro na vertical. A nova renderização usa exatamente essas contas. O topo físico do corpo neutro é calibrado em 1,80 m. A altura da caixa de pixels pode passar de 94 px porque também inclui perspectiva dos pés e contorno; não a igualamos achatando direções.

O canvas do rig passou de 96×96 para **128×128**, com apoio **(64,112)**. A geometria é rasterizada diretamente nessa escala; não esticamos um PNG pronto. A proporção corporal e a inclinação da câmera foram preservadas.

## Direção da grade versus direção da tela

A correspondência vem de [`shared/src/protocol.ts`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/shared/src/protocol.ts) e [`shared/src/pathfinding.ts`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/shared/src/pathfinding.ts).

| `Token.dir` | Passo na grade `(dx,dy)` | Sprite / tela |
| --- | --- | --- |
| 0 | (0,-1) | NE |
| 1 | (1,-1) | E |
| 2 | (1,0) | SE |
| 3 | (1,1) | S |
| 4 | (0,1) | SW |
| 5 | (-1,1) | W |
| 6 | (-1,0) | NW |
| 7 | (-1,-1) | N |

As folhas continuam em N, NE, E, SE, S, SW, W, NW. O mapeamento fica explícito no perfil e nos metadados. Os testes comparam o vetor de frente do corpo projetado com o passo real da grade para as oito direções.

## Exportação compatível

```bash
spriteforge crona demo-input/humanoid-base/manifest.json --output dist/crona
```

O pacote contém `crona/humanoid-base/tabuleiro-3d/`:

- `anim.json`, com `versao: 2`, estado `desarmado` e direções minúsculas.
- `parado-desarmado-<dir>.png`, com quatro quadros lado a lado.
- `andar-desarmado-<dir>.png`, com seis quadros lado a lado.
- Âncora, dimensões, quantidade de quadros, pés por quadro e distância por ciclo.

O formato foi conferido em [`server/src/portraits.ts`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/server/src/portraits.ts), [`client/src/render/sprites.ts`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/client/src/render/sprites.ts) e [`client/src/room/RoomView.ts`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/client/src/room/RoomView.ts).

O CRONA aplica uma escala legada às pessoas. O pacote usa a inversa exata dessa escala para preservar **1 pixel do sprite = 1 pixel do tabuleiro no zoom 1**. O andar no jogo vem da distância percorrida; `casasPorCiclo` considera também o fator legado do `RoomView`. O GIF continua sendo uma prévia de tempo, não uma simulação completa da movimentação do servidor.

Os pontos dos pés vêm da articulação e do volume do corpo-base; não são detecção automática do contorno de qualquer roupa. Novas botas e outros tipos de corpo precisam conferir esses pontos.

**Este pacote não foi instalado no CRONA nem substitui o Alosi.** É a entrega de estudo pronta para revisão visual e futura integração. Armado, machucado e outras ações ainda não estão implementados.

## Prévia sobre o piso

`scripts/render_crona_preview.py` usa a textura real [`piso-0-0.png`](https://github.com/FelipeSiqueiraDev/CRONA/blob/f08bea3816fe2af49a98975341b0c6fe4eebf158/client/public/arte/texturas/px/cozinha_fazenda/piso-0-0.png), copiada sem alteração para `integrations/crona/floor-tile.png`. A imagem de conferência mostra as oito vistas em uma grade 64×32 e indica o número de direção correspondente. É uma comparação no piso, não uma captura da sessão ao vivo nem uma validação de ocultação por todos os móveis.
