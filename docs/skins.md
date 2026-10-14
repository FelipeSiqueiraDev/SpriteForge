# Skins dos lugares existentes

O CRONA continua sendo a fonte da planta, dos objetos, das medidas e das interações. O SpriteForge organiza e exporta a aparência sobre esses mesmos objetos: PNGs por giro/estado, âncoras, texturas de piso e parede e um catálogo de cobertura. O primeiro perfil é `crona-cozy-v1`.

A primeira entrega reaproveita o renderizador de cozinha que já existe no CRONA. Isso mantém a linguagem visual do tabuleiro: madeira quente, materiais com textura, contornos finos, sombreamento por face e pixel nativo. A cozinha completa serve como referência de composição. No jogo, cada móvel e cada trecho de piso/parede continuam sendo peças separadas.

## Primeiro lote

O catálogo inicial registra 268 objetos: 221 de piso e 47 de parede. Este perfil entrega nove modelos, com quatro giros reais por modelo e o estado aceso adicional do fogão: 40 PNGs de móveis. Os outros 259 objetos ficam na fila deste perfil. Esse número mede a cobertura do novo perfil; alguns desses objetos já têm outras artes no CRONA.

Modelos: `armario_cozinha`, `armario_cozinha_l`, `fogao_lenha`, `pia_cozinha`, `mesa_cozinha`, `chair_wood`, `crate_wood`, `barrel` e `plant`. Piso e paredes recebem mais 24 imagens nativas com `px.json`, associadas exclusivamente ao estilo `cozinha_fazenda`.

O pacote tem:

| Arquivo | Uso |
| --- | --- |
| `index.html` | Galeria offline com busca, giros, estados e pendências |
| `skins.json` | Objetos, definições originais e cobertura do perfil |
| `requests.json` | Objetos aguardando receita/arte, com suas medidas e estados |
| `moveis.patch.json` | Somente os nove modelos entregues |
| `moveis.merged.json` | Proposta de manifesto unida ao original, preservando outros modelos e vistas táticas |
| `texturas.patch.json` | Associação do piso/parede da cozinha |
| `texturas.merged.json` | Proposta unida ao catálogo de texturas original |
| `client/public/arte/` | PNGs de móveis, pisos e paredes |
| `previews/cozinha.png` | Referência visual do cômodo; não substitui o cenário interativo |

## Gerar no GitHub

Abra [Actions → CRONA Skins](https://github.com/FelipeSiqueiraDev/SpriteForge/actions/workflows/skins.yml), execute em `main` e baixe o artifact `crona-skins-…`. Extraia e abra `crona-cozy-v1/index.html`. O pacote é retido por 30 dias; fontes, perfil, hashes e catálogo estão no GitHub e permitem reproduzir a entrega. A imagem piloto também fica no repositório.

Cada execução lê as definições atuais de `shared/src/furni.ts`. Um objeto criado com o Claude aparece automaticamente na fila na próxima execução, mesmo sem arte. O importador lê somente as duas listas do código confiável do próprio CRONA, sem iniciar o jogo nem acessar o banco. Se a sintaxe dessas listas mudar, o importador precisa de revisão.

O exportador só gera os modelos que têm receita. Ele não inventa automaticamente uma skin para qualquer objeto novo. Os hashes dos renderizadores impedem mudanças silenciosas no resultado; quando o código artístico mudar, revisar a imagem e atualizar `integrations/crona/skin-source-lock.json`. Uma mudança na pegada de um modelo do lote também bloqueia a exportação até revisar a receita.

Para desenvolvimento:

```bash
python -m pip install .
node scripts/import_crona_catalog.cjs ../CRONA/shared/src/furni.ts build/catalog.json
spriteforge skins --source ../CRONA --catalog build/catalog.json
```

`rules` no perfil documenta a direção de arte. Os materiais efetivos vêm dos renderizadores do CRONA; editar apenas esses valores no JSON não repinta as imagens.

## Contrato visual

IDs, categoria, footprint, altura de uso, interações e estados permanecem no CRONA. A medida `real` da arte representa o modelo desenhado, e pode incluir encosto ou chaminé; ela não substitui a altura de assento/empilhamento da definição. O desenho usa piso 64×32, câmera de 30° e `pixel: true`, `exato: true`, `escala: 1`.

Uma skin só fica completa quando possui todas as vistas e estados exigidos pelo objeto. Imagens ausentes, sem conteúdo, fora da pasta, âncoras inválidas e IDs desconhecidos são erros de entrega. O contorno/material é pixel art; sombras de contato podem ter alpha parcial, como no renderizador nativo. A regra de alpha binário dos personagens não se aplica a essas sombras.

Este primeiro exportador produz objetos de piso com `giros`. Itens de parede já entram na fila; suas receitas futuras deverão entregar `parede.l`/`parede.r` e estados conforme o consumidor do CRONA, com validação própria. Tapetes, variantes por material e outros formatos também exigem receitas específicas.

## Integração no jogo

A entrega está no SpriteForge. Nenhum arquivo do CRONA foi alterado ou instalado automaticamente. O guia [para o Claude](handoff-claude-skins.md) descreve a instalação e a evolução para seleção de perfil por cômodo.

O manifesto unido preserva modelos não entregues, `cima`, `cimaEstados` e `encosta`. Coordenadas antigas de `chamas`, `brilho` e `tela` não são copiadas sobre uma imagem de tamanho diferente: precisam ser calculadas para a nova arte. O fogão exportado inclui uma imagem acesa estática; animação de fogo é uma integração posterior. Confira o encaixe, sobreposição, giros e uso do mapa tático no jogo antes de aprovar a instalação.
