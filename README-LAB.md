# Kellvyn — laboratório de paridade Web × Android

Este repositório é o laboratório isolado para medir, documentar e corrigir diferenças entre a interface web aprovada e o aplicativo Android nativo. O repositório principal permanece separado: nenhuma correção é publicada nele automaticamente.

## Repositórios e fontes

- Laboratório: `ar2233789-oss/Ia-kellvyn-`
- Aplicativo principal e destino futuro do APK de distribuição: `ar2233789-oss/kellvyn-ai-assistant`
- Snapshot web e Android: diretório `snapshot/`
- Revisão de origem congelada: `8e6d4456f0ceec57a65f5a078c26277e447d68bf`
- A aparência web aprovada é protegida por `snapshot/SOURCE-LOCK.json`; o workflow falha se os arquivos visuais protegidos mudarem.

## Verificações automáticas

O workflow `.github/workflows/lab-validation.yml` executa:
1. testes do comparador de screenshots e sequências;
2. verificação de paridade do prompt, proteção, memória, modelo, SDK e parâmetros de geração da IA;
3. verificação de integridade da referência web aprovada;
4. testes e build da aplicação web;
5. testes unitários, compilação, integridade e assinatura do APK Android.

O workflow `.github/workflows/visual-capture.yml` cria o AVD `PocoF6Virtual` do laboratório original (Android 15/API 35, 1220×2712, 440 dpi, 8 GB RAM, 4 vCPU e SwiftShader). Dentro da mesma sessão desse AVD, abre a versão web no APK auxiliar WebView e depois abre o APK Android nativo. Captura os mesmos estados, compara pixels sem redimensionar e produz overlays, heatmaps, diffs e JSON. As capturas são artefatos temporários da execução; não são commitadas no repositório. A comparação é diagnóstica e não declara pixel-perfect automaticamente.

O APK `lab-reference-android` existe somente para comparar a página web no mesmo Android virtual. Ele não é parte do projeto `snapshot/android` nem será copiado para o APK de distribuição. O `studio/index.html` é uma oficina independente e offline. O workflow `.github/workflows/studio-workbench.yml` valida a estrutura HTML/JavaScript e executa testes Playwright de comparação, exportação, efeitos, paletas, arte 2D, projeção 3D/4D, linha do tempo e relatórios. O Studio não modifica automaticamente o app.
A captura Android é conduzida por `scripts/capture_native_ui.py`: verifica a árvore de acessibilidade, reconhece e tenta recuperar o diálogo `System UI isn't responding`, localiza controles por texto/descrição e registra diagnósticos quando a UI não responde. Os seletores são cobertos por `scripts/test_capture_native_ui.py`.

## Áreas cobertas

- `animation-catalog/`: chuva, neve, folhas, raios, indicador de pensamento e microfone.
- `visual-tests/`: protocolo e matriz de paridade.
- `ai-evaluation/`: casos comportamentais e contratuais para a mesma IA em web e Android.
- `studio/index.html`: Studio offline de produção com comparador de screenshots, editor de paletas, iluminação, prancheta 2D, cubo 3D, projeção 4D, linha do tempo e análise de logs/vídeos.
- `lab-reference-android/`: APK auxiliar de laboratório que renderiza a versão web dentro de uma WebView no próprio Android; pacote separado, não incluído no APK Kellvyn.
- `scripts/`: comparadores, alinhamento, captura nativa resiliente, verificadores de paridade e testes do Studio.
- `evidence/`: evidências e relatórios de cada execução.
- `poco-f6-lab/`: parâmetros e limitações do AVD.

## Critérios de aprovação

- Mesma resolução lógica, conteúdo, paleta e estado interativo.
- Recortes documentados para as barras do sistema; sem interpolação ou redimensionamento.
- Animações verificadas por sequências de quadros sincronizados, não apenas por uma imagem estática.
- Diferenças registradas em números e imagens; “pixel-perfect” só com igualdade integral.
- AVD Android 15 é apenas um ambiente aproximado. A aprovação final no Poco F6 exige captura e teste no aparelho físico com HyperOS.

## Segurança do projeto principal

O laboratório não faz merge, release nem publicação no repositório principal. Só uma revisão aprovada e com evidências pode ser levada ao projeto de distribuição.
