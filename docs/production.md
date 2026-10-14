# Processo para os personagens Hydra

## Piloto: Alosi

1. Conferir as referências já aprovadas do personagem e do mapa, incluindo óculos e altura.
2. Definir escala e câmera olhando um sprite parado sobre o mapa real.
3. Aprovar oito vistas paradas: silhueta, roupas, rosto e detalhes assimétricos.
4. Construir a caminhada em seis poses por direção, com braços e pernas contralaterais.
5. Revisar todos os loops: contato, passagem, apoio oposto, passagem oposta e transição de volta ao primeiro frame. Não repetir o primeiro frame no final.
6. Rodar a validação e conferir a prévia frame a frame.
7. Testar no tabuleiro antes de marcar como pronto e aplicar o processo aos outros três protagonistas.

## Regras artísticas

- Iluminação neutra e consistente: sem glow, vinheta ou luz dramática nos sprites de jogo.
- Cor, tamanho da cabeça e proporção do corpo preservados entre direções.
- Câmera definida pelo mapa real; a projeção do manequim é apenas diagnóstico.
- Não usar simples flip quando óculos, roupas, cabelo, equipamentos ou marcas forem assimétricos.
- Não criar caminhada apenas deslizando um recorte rígido de perna ou braço: articulações, ocultação e redesenho por pose precisam fazer sentido.
- Separar identidade artística e mecânica da animação; um template pode orientar movimento, mas não substituir o desenho do personagem.

O sistema inicial recebe frames desenhados. O manequim é um exemplo programático. A ferramenta **ainda não converte automaticamente uma ilustração em um personagem animado** e não contém um editor Aseprite integrado.

## Aprovação visual por direção

| Conferência | Critério |
| --- | --- |
| Identidade | Continua sendo o mesmo personagem, incluindo detalhes pequenos |
| Proporção | Sem achatamento ou crescimento acidental |
| Câmera | Mesma perspectiva do mapa e das outras direções |
| Contato | Pé apoiado sem deslizar em relação ao deslocamento do token |
| Movimento | Pernas e braços coordenados, sem membros duplicados |
| Loop | Último → primeiro sem salto |
| Arquivos | PNGs íntegros, transparência e apoio corretos |

Para criaturas, tamanho de célula, silhueta, número de membros e movimento serão definidos por categoria. Não forçaremos monstros no template humano.
