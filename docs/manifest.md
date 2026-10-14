# Contrato de origem e exportação

Cada personagem tem um ID exclusivo, uma célula fixa e um ponto de apoio comum a todos os seus frames. `pivot` é a posição na célula que o tabuleiro deve ancorar no chão. Não é calculado automaticamente.

Exemplo completo de uma ação idle de um frame por direção:

```json
{
  "version": 1,
  "id": "meu-personagem",
  "name": "Meu personagem",
  "cell": [96, 96],
  "pivot": [48, 80],
  "animations": {
    "idle": {
      "frame_count": 1,
      "duration_ms": 200,
      "directions": {
        "N": ["frames/idle/N/00.png"],
        "NE": ["frames/idle/NE/00.png"],
        "E": ["frames/idle/E/00.png"],
        "SE": ["frames/idle/SE/00.png"],
        "S": ["frames/idle/S/00.png"],
        "SW": ["frames/idle/SW/00.png"],
        "W": ["frames/idle/W/00.png"],
        "NW": ["frames/idle/NW/00.png"]
      }
    }
  }
}
```

Para walk, use seis caminhos por direção, de `00.png` a `05.png`. A ferramenta respeita a **ordem explícita da lista**, sem adivinhar nomes ou ordenar arquivos. Todos os caminhos precisam estar dentro da pasta do manifesto. Células podem ter até 512×512 px; cada ação, até 64 frames por direção.

`duration_ms` precisa ser múltiplo de 10, entre 10 e 2000 ms, por causa da resolução temporal do GIF. Cada ação pode ter quantidade e duração diferentes. A duração se aplica a todos os frames daquela ação.

## Saída por personagem

- `<ação>.png`: linhas em N, NE, E, SE, S, SW, W, NW; colunas em ordem temporal.
- `frames/<ação>/<direção>/<índice>.png`: PNGs individuais, pixels preservados.
- `<ação>-<direção>.gif`: prévia ampliada em 3× por nearest-neighbor, com fundo opaco.
- `atlas.json`: coordenadas de recorte, dimensões, duração e pivot de cada frame.
- `report.json`: bounding boxes, cores visíveis, distâncias do apoio e avisos.
- `index.html`: prévia local, sem bibliotecas externas ou requisições de rede.

O tabuleiro deve usar o PNG e o atlas para renderizar. **GIF é só prévia.** Não há integração com o código do tabuleiro nesta entrega.

## Erros e avisos

Erros impedem exportação: ausência de direções/frames/arquivos, tamanho errado, alpha parcial, desenho vazio ou encostado na borda. A ferramenta exige uma margem de pelo menos um pixel; encostar na borda não prova corte, mas exige revisão.

Avisos não impedem exportação: muitos tons, todos os frames idênticos, variação grande do topo ou distância entre o último pixel visível e o apoio. Roupas longas, armas, caudas e monstros podem justificar esses avisos. A primeira versão usa limites de diagnóstico fixos, não regras artísticas universais.

Altura constante da célula é uma propriedade técnica. A altura visível pode variar por perspectiva, pose ou movimento. Não achatamos um sprite para fazê-lo passar em uma medida.
