# Base chibi e animações v3

**Estado: visual rejeitado pelo usuário.** A cabeça e as proporções deste manequim não atenderam ao pedido. Os testes descritos abaixo validam aspectos técnicos, sem comprovar fidelidade ou qualidade visual. A abordagem atual está registrada em [caminhada desenhada a partir da referência](../art-direction/chibi-reference-walk/README.md). Este documento preserva o estudo procedural como histórico.

A nova geometria adapta a direção visual aprovada para uma base articulada, com rosto/mandíbula definidos, tronco estruturado, mangas, calça e sapatos. Ela não recorta nem deforma a imagem conceitual. Cada direção e pose é rasterizada pela câmera do CRONA, com profundidade por pixel. A versão v2 continua disponível, sem substituir as receitas antigas.

## Entrega

| Aparência | Origem | Animações |
| --- | --- | --- |
| `chibi-base` | `chibi-base.json` | idle: 4 × 8; walk: 6 × 8 |
| `chibi-outfit-demo` | `chibi-outfit-demo.json` | mesmas poses, peças e cores de teste |

São 80 PNGs por aparência, além de folhas, GIFs, atlas, relatório, máscaras de visibilidade e pacote CRONA `anim.json` v2. As duas novas aparências somam 160 frames de origem. O pacote geral também preserva a demonstração e as duas bases v2 para comparação.

O corpo chibi tem um crânio volumétrico com face inferior afunilada, olhos/íris em geometria, sobrancelhas e boca ajustadas à superfície. A iluminação tem preenchimento ambiente e cinco tons possíveis por material. Não há antialiasing nos PNGs renderizados. A máscara de partes registra a superfície visível, não uma coleção completa de peças escondidas.

## Movimento

Pernas usam duas seções de 10 unidades e braços duas de 6,8 unidades. A cinemática mantém esses comprimentos durante as poses. Os braços acompanham a perna contrária. Durante o apoio, a posição longitudinal do pé varia linearmente em sentido contrário ao avanço do corpo; durante o balanço, o pé sobe e avança por uma curva suave. Há apoio duplo nas duas poses de contato e elevação do pé nas poses intermediárias.

A passada nominal é de 16,8 unidades por loop, cerca de **0,476 m** na escala do CRONA. Seis frames de 100 ms formam o ciclo de 600 ms. A tradução de `casasPorCiclo` respeita o fator legado do jogo. O rig registra os pontos físicos dos pés por pose; o exportador usa esses pontos, mantendo o cálculo anterior como fallback para os estudos v2.

O teste de apoio verifica que pé + avanço do corpo permanece constante durante a fase plantada, incluindo a passagem entre ciclos. Isso verifica o modelo matemático; sincronização com servidor, colisões, sobreposição dos móveis e sensação de movimento ainda precisam ser conferidas numa sessão real do CRONA.

O relatório heurístico sinaliza dois frames em cada nova aparência: as pontas dos sapatos ficam 11 px além do centro vertical declarado durante o contato diagonal. Os sprites mantêm margem e os pontos físicos de apoio vêm das poses. A entrega conserva esses avisos para revisão, sem deformar ou deslocar frames para eliminá-los.

## Gerar

```bash
python -m pip install .
spriteforge rig templates/humanoid/chibi-base.json --output demo-input --workers 2
spriteforge rig templates/humanoid/chibi-outfit-demo.json --output demo-input --workers 2
spriteforge build demo-input/chibi-base/manifest.json --output dist
spriteforge build demo-input/chibi-outfit-demo/manifest.json --output dist
spriteforge crona demo-input/chibi-base/manifest.json --output dist/crona
spriteforge crona demo-input/chibi-outfit-demo/manifest.json --output dist/crona
spriteforge wardrobe dist/chibi-base dist/chibi-outfit-demo --output dist/chibi-wardrobe.html
```

`--workers` aceita de 1 a 8 processos; a ordem dos frames no manifesto é preservada. O padrão continua sendo um processo. O workflow usa dois processos e inclui as referências no pacote, junto das prévias.

`python scripts/audit_chibi_exports.py` confere os 160 frames efetivamente gerados, a preservação dos pixels nas folhas/tiras, os pontos dos pés exportados e amostras da associação dos frames produzidos em paralelo. O resultado fica em `dist/chibi-validation.json`.

## Revisão e continuidade

Abra `wardrobe.html` no pacote de Actions para trocar aparência e ação, pausar, avançar um frame, ajustar velocidade e conferir o apoio. `previews/chibi-walk.gif` mostra o ciclo nas oito direções; `chibi-modular.gif` compara a base com as peças; `chibi-crona-walk.gif` mostra o personagem sobre o piso do jogo.

A direção artística aprovada e a sua adaptação geométrica são arquivos diferentes. A nova animação é um estudo revisável, não uma aprovação automática de qualidade artística. Conferir especialmente rosto de perfil, volume/silhueta, coordenação dos braços, contato do pé e passagem do último para o primeiro frame. Não esticar imagens para igualar alturas, nem espelhar direções para fabricar vistas assimétricas.

A base segue o perfil de câmera de 30°, célula 128×128 e apoio (64,112). O topo neutro continua calibrado em 1,80 m. Cabelo e outros acessórios podem acrescentar altura visual. Remover `outfit` e os acessórios da receita permite renderizar o manequim neutro com o mesmo esqueleto.

Ainda faltam as peças e a identidade específicas dos quatro protagonistas, começando pelo Alosi. Ações armado, ataque e machucado e outras proporções corporais exigem poses/peças próprias. Esta revisão não instala os estudos no CRONA e não altera o sistema de skins de ambientes.
