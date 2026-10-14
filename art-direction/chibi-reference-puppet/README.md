# Carequinha: movimento contínuo por partes

O usuário aprovou o caminho de animar o desenho de referência, mas apontou variações e braços que pareciam bugados no loop de quatro desenhos. Esta prova usa um único conjunto de dez peças raster, preparado pelo imagegen com referência à imagem original. Não gera um novo rosto ou novos braços em cada quadro.

`parts.png` contém cabeça/pescoço, tronco/pelve, dois pares de braço/antebraço e dois pares de coxa/canela com sapato. Os prompts novos de criação e correção das junções estão em `prompts.txt`. A arte foi preservada sem substituir a imagem original aprovada.

`scripts/reference_puppet.js` monta o personagem em canvas com articulações de dois segmentos, braços contrários à passada e comprimentos constantes. O crânio usa sempre o mesmo bitmap, sem deformação ou rotação, com translação inteira para evitar oscilação dos pixels. Os sapatos ficam nivelados durante o apoio, independentemente da inclinação da canela. O balanço dos pés tem velocidade contínua nas transições.

```bash
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install chromium
node scripts/build_reference_puppet.cjs art-direction/chibi-reference-puppet/parts.png dist/previews/reference-puppet
python scripts/encode_reference_puppet.py dist/previews/reference-puppet
```

O gerador cria uma prévia HTML autossuficiente, 32 quadros transparentes, 32 quadros com fundo de revisão, prancha de poses, GIF, APNG e registros de rig/validação. O loop tem 960ms, com 32 quadros de 30ms. `SPRITEFORGE_CHROMIUM` pode indicar um executável local; sem essa variável, o Playwright usa seu navegador padrão.

A validação confere os pixels registrados da cabeça em todos os quadros, os comprimentos dos membros, o fechamento de pose, os controles da prévia e a largura de celular. A codificação confere o roundtrip dos pixels no APNG e a cabeça consistente no GIF. Esses testes não aprovam a anatomia nem a sensação de caminhada.

Limites: é um teste 2D em uma vista, ainda com emendas de peças e movimento no plano da imagem. Não substitui vistas próprias das oito direções. Não há calibração física ou integração no CRONA; contato dos pés no jogo e aprovação visual continuam pendentes. A roupa é parte das peças desta prova, sem o guarda-roupa completo. A base v3 procedural e a primeira folha de caminhada permanecem como estudos anteriores, não como resultados aprovados.
