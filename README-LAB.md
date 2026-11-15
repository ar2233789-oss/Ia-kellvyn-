# Kellvyn — laboratório de paridade Web × Android

Este repositório é isolado do projeto principal e serve para medir, documentar e corrigir diferenças entre a interface web de referência e o aplicativo Android nativo.

## Regra central
A versão web é a referência visual e comportamental. Nenhuma alteração no aplicativo principal deve ser considerada aprovada sem evidência reproduzível neste laboratório.

## Estrutura
- `web-reference/`: capturas, metadados e versão web de referência, preservada sem alterações.
- `android-native/`: APK, metadados de build e capturas da versão nativa.
- `animation-catalog/`: inventário de animações, parâmetros e critérios de equivalência.
- `visual-tests/`: procedimentos e ferramentas de comparação de imagens e vídeos.
- `poco-f6-lab/`: configuração do ambiente Android e limitações do emulador.
- `evidence/`: relatórios, logs, capturas e resultados por execução.

## Estado inicial
O esqueleto e os critérios estão sendo preparados. Nenhum teste de paridade é declarado aprovado até existirem capturas correspondentes da web e do Android no mesmo estado, dimensões e escala.

## Segurança do projeto original
Este laboratório não altera nem mescla automaticamente mudanças no repositório principal.
