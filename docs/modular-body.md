# Corpo-base e aparência

O primeiro corpo-base é um manequim neutro, careca, sem barba, roupa ou marcas. Tem volume, proporção compacta e câmera elevada de 30°. É um **estudo para aprovação visual**, não um personagem final.

## Como vestir o mesmo corpo

`templates/humanoid/base.json` descreve a aparência neutra. `outfit-demo.json` troca apenas a aparência: camisa, calça, botas, cabelo, barba, óculos e cicatriz. As duas receitas usam a mesma geometria corporal, câmera, articulações e sequência de poses.

Os volumes das roupas acompanham as articulações. Cabelo, barba, óculos e marcas acompanham a cabeça. Um buffer de profundidade decide qual superfície está visível em cada pixel; por isso, os acessórios do rosto não aparecem através da cabeça quando ela vira de costas.

Esta primeira biblioteca contém **peças procedurais simples**. Não há ainda um editor visual para desenhar roupas. Um sobretudo, capuz volumoso, cabelo longo ou equipamento específico precisa de sua própria geometria/peça e movimento. Não basta aplicar uma imagem frontal sobre todos os ângulos.

## Gerar e comparar

```bash
spriteforge rig templates/humanoid/base.json --output demo-input
spriteforge rig templates/humanoid/outfit-demo.json --output demo-input
spriteforge build demo-input/humanoid-base/manifest.json --output dist
spriteforge build demo-input/humanoid-outfit-demo/manifest.json --output dist
spriteforge wardrobe dist/humanoid-base dist/humanoid-outfit-demo --output dist/wardrobe.html
```

No GitHub, o workflow já faz essas etapas. No pacote exportado, `wardrobe.html` alterna entre as duas aparências pré-renderizadas. Não gera novas roupas no navegador.

Para uma aparência nova, copie a receita, dê um ID exclusivo e ajuste as cores/peças. Os slots aceitos nesta versão são:

| Campo | Uso |
| --- | --- |
| `body_color` | Cor do manequim/corpo |
| `outfit.shirt` | Camisa simples e mangas articuladas |
| `outfit.trousers` | Calça seguindo pernas e quadril |
| `outfit.boots` | Botas seguindo os pés |
| `hair` | Cabelo curto de teste |
| `beard` | Barba curta de teste |
| `glasses` | Armação acompanhando a cabeça |
| `scar` | Marca de teste na lateral do rosto |

As cores usam `#RRGGBB`; `null` remove o acessório ou a roupa inteira. Alterar uma receita não altera o esqueleto. Os slots representam o corpo esquerdo/direito, não o lado da tela; não fazemos flip dos sprites.

## Movimento e integração

A caminhada usa seis poses e 600 ms por loop. A perna de apoio passa para trás enquanto a outra sobe e avança. Braços e pernas se alternam de forma contralateral. O joelho é calculado com duas seções de comprimento fixo; não esticamos a perna de uma pose para outra.

`rig.json` registra articulações, apoio de cada pé e o deslocamento nominal: 22 unidades do mundo por loop. São dados de diagnóstico e futura sincronização. O tabuleiro ainda precisa relacionar esse deslocamento com sua própria escala e velocidade; a ferramenta não garante ausência de deslizamento durante o movimento do token.

`parts/` contém máscaras com IDs por parte visível. Elas ajudam a conferir ocultação. Não são camadas completas que restauram automaticamente as superfícies escondidas; para tirar uma roupa, regenere o sprite com esse slot desativado.

## Próxima aprovação

Conferir corpo neutro parado e andando: altura, cabeça, ombros, comprimento das pernas, câmera e loop. Depois, construir as peças específicas do Alosi com as referências aprovadas. O exemplo vestido **não representa o Alosi**.

O plano de biblioteca é ter bases com proporções diferentes — padrão, robusta, pequena e categorias de criaturas — mantendo câmera e escala coerentes. Essas outras bases ainda não estão implementadas.
