# Caminhada a partir do desenho de referência

**Estudo anterior.** O usuário apontou variações e braços que pareciam bugados nesta primeira sequência. A prova atual usa [peças fixas e movimento contínuo](../chibi-reference-puppet/README.md).

O usuário rejeitou a cabeça e as proporções do manequim procedural v3. Pediu animar o próprio carequinha da referência, com proporções aceitáveis. Esta pasta registra a mudança de abordagem: quadros desenhados pelo imagegen usando a imagem aprovada como referência direta.

`identity-master.png` é a tentativa de isolar a vista de três quartos da imagem original preservada em `../chibi-v3/approved-concept.png`. `walk-sheet.png` é a segunda versão da folha de seis quadros. Os prompts novos estão em `prompts.txt`.

O empacotador escolhe os quadros 1, 2, 4 e 5: contato e passagem de cada metade do ciclo. Os outros dois desenhos gerados repetem poses de contato sem acrescentar uma fase útil. O alinhamento aplica somente translação; as cópias de 128px usam escala uniforme. O script não reconstrói, achata ou deforma a cabeça.

```bash
python scripts/assemble_reference_walk.py art-direction/chibi-reference-walk/walk-sheet.png dist/previews/reference-walk
```

A saída inclui GIF de revisão, APNG com transparência, quatro PNGs de 512px, quatro cópias de 128px, uma prancha e metadados de alinhamento. O GIF tem quatro quadros de 180ms, total de 720ms. A arte original é preservada sem sobrescrita.

É uma primeira prova em uma direção, ainda sem aprovação visual. As poses geradas apresentam pequenas diferenças de rosto, roupa e orientação do tronco; a suavidade, os contatos dos pés e a consistência precisam de refinamento. Não é um ciclo final em oito direções, nem uma exportação calibrada ou instalada no CRONA. Os testes do rig procedural não validam esta animação desenhada.
