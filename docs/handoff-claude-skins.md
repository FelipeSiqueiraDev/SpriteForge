# CRONA: objeto primeiro, skin depois

O fluxo combinado é: Claude cria o objeto funcional no CRONA; SpriteForge produz e valida a aparência para o mesmo ID. A planta do lugar já criado permanece a fonte da cena. O lote piloto e seu contrato estão em [skins.md](skins.md).

## Criar um móvel sem arte

Cadastre o ID em `FURNI_METERS` ou `WALL_FURNI_LIST`, com footprint, rotações, estados e interações. Use o renderer procedural enquanto a skin não existir. Não aumente uma cadeira, mude a colisão ou altere um seed para acomodar um PNG. Execute **CRONA Skins** no SpriteForge: o importador adiciona o objeto à fila `requests.json` sem precisar de uma receita de arte.

Depois, a receita artística entrega as vistas exigidas e sua âncora, no pixel nativo. Para cadeiras, `height` pode ser a altura de assento; a imagem deve incluir o encosto. O catálogo preserva essa distinção.

## Instalar o piloto disponível

1. Baixe o artifact de **CRONA Skins** e confira os nove modelos no `index.html`, inclusive todos os giros e os dois estados do fogão.
2. Copie os PNGs de `client/public/arte/mobiliario/<id>/` e `client/public/arte/texturas/px/crona_cozy_cozinha/` para os mesmos caminhos do CRONA.
3. Una `moveis.patch.json` ao manifesto atual. `moveis.merged.json` é uma proposta já unida ao estado do CRONA lido pela execução; se o jogo avançou depois, refaça a união sobre o manifesto mais recente.
4. Una `texturas.patch.json` a `texturas.json`. Troque apenas `cozinha_fazenda`; não substitua `ladrilho`, usado por outros lugares.
5. Confira âncoras, camadas, dimensões, mapa tático, interação e rotações. Metadados de luz/fogo/tela usam coordenadas da imagem: recalcular para esta arte antes de restaurar os efeitos animados. A imagem de fogo deste primeiro lote é estática.
6. Siga `AGENTS.md` do CRONA para branch, revisão e verificações. Não substitua o manifesto inteiro apenas pelos nove objetos do patch.

A instalação simples usa os IDs existentes e pode atualizar a aparência desses modelos também em outros cômodos. Para escolher uma aparência por lugar, a extensão abaixo deve entrar no código com o Claude.

## Evoluir para perfil por cômodo

Adicione um `skinProfile` opcional ao cômodo, por exemplo `crona-cozy-v1`, sem mudar a planta. Mantenha o catálogo de artes do perfil separado do catálogo base. A ordem sugerida é:

| Condição | Aparência |
| --- | --- |
| Cômodo sem perfil | Comportamento atual do CRONA |
| Perfil com vista válida para ID, giro e estado | PNG da skin, com sua âncora e escala nativa |
| Perfil sem a vista exigida | Renderer procedural do objeto |
| Skin pendente/incompleta | Renderer procedural e indicação de pendência no editor |

Resolver por instância/cômodo evita que vestir a cozinha troque todas as cadeiras da sede. Se a regra escolhida for usar a arte base antiga antes do procedural, tornar isso explícito; o catálogo do novo perfil registra a ausência de skin mesmo quando existe arte antiga.

Carregue móveis, texturas e luzes do mesmo perfil. Preserve cache por perfil, estado e giro, desenho sem suavização, ordem de profundidade e comportamento das interações. Uma falha ao carregar a imagem também deve chamar o procedural. A peça precisa continuar selecionável e utilizável durante a troca de visual.

O SpriteForge entrega a produção e a fila. A seleção de perfil por cômodo ainda precisa dessa implementação no CRONA; ela não está instalada neste lote.
