# Objetivo permanente de execução — Kellvyn

## Missão
Concluir o layout e a paridade funcional do aplicativo Android Kellvyn comparando a referência web congelada, renderizada dentro do APK auxiliar WebView, com o APK Android nativo no perfil PocoF6Virtual.

A tarefa não é apenas compilar o APK. É inspecionar as duas renderizações no mesmo dispositivo virtual, medir as diferenças, corrigir o candidato Android e repetir o ciclo até não restarem divergências conhecidas sem justificativa.

## Ambientes
- Referência: `snapshot/src/components/kellvyn/` e `snapshot/src/styles.css`. Não alterar a referência aprovada durante o trabalho de paridade.
- Candidato: `snapshot/android/`. As correções de layout e comportamento devem ser feitas aqui.
- Referência WebView: `lab-reference-android/`. É exclusivamente uma ferramenta de laboratório; nunca deve ser incorporada ao APK de distribuição.
- Dispositivo virtual: `PocoF6Virtual`, Android 15/API 35, 1220 × 2712 px, 440 DPI, 8 GB de RAM e 4 vCPU, com modelo-base Pixel 7 e substituições do perfil Poco F6.
- Distribuição: somente depois da validação, transferir o resultado para o repositório principal `ar2233789-oss/kellvyn-ai-assistant`.

## Escopo obrigatório de comparação
1. Tela principal vazia e tela com mensagens, mensagens longas e ações da resposta.
2. Cabeçalho, histórico aberto/fechado, menu + aberto, seletor de arquivos e prévia/remoção de anexos.
3. Barra inferior: AI, Navegador, Editor, Terminal, Bots e Apps.
4. Configurações no topo, meio e fim da rolagem; todas as paletas, cores HEX e persistência.
5. Efeitos isolados e combinados: chuva, chuva + raios, neve, folhas e alternância repetida.
6. Indicador de pensamento e microfone: estado ocioso, ativo, permissão/erro e encerramento.
7. Painéis: histórico, navegador, editor, bots, plugins, apps do celular e memória.
8. Teclado, barras do sistema, rolagem, estados de envio, restauração após morte de processo e ausência de congelamentos/ANRs.

## Critério de validação
- Capturar referência e candidato no mesmo PocoF6Virtual, com mesma resolução, densidade, conteúdo e estado de interação.
- Guardar PNGs originais, overlays, diff/heatmaps, métricas e relatórios JSON.
- Animações devem ser avaliadas com sequências temporais sincronizadas; um screenshot isolado não prova equivalência.
- Não tratar compilação, assinatura ou abertura do APK como prova de paridade visual.
- Corrigir cada diferença confirmada no candidato Android, reconstruir, repetir a comparação e registrar o resultado.
- Diferenças de conteúdo que violem regras do produto (por exemplo, oferecer seletor de outras IAs/provedores quando a regra é uma única Kellvyn) devem ser preservadas como restrições explícitas; não introduzir um recurso proibido só para reduzir diferença de pixels.
- Não declarar “100%”, “finalizado” ou “perfeito” sem evidência cobrindo o escopo acima. Quando uma diferença depender de renderização aleatória ou de conteúdo incompatível, documentar o limite e o motivo.

## Regras de preservação
- Não modificar partes da referência web já aprovadas.
- Não adicionar WebView ao APK de distribuição.
- Não introduzir modo leve/pesado, seletor de provedores/modelos, conceitos de núcleo ou tokens na interface principal.
- Preservar a identidade visual e os controles aprovados; corrigir o candidato, não redesenhar o projeto.
- O Studio e os instrumentos de laboratório são ferramentas para validar o aplicativo, não substitutos da aplicação final.

## Ciclo de execução
Inventariar → capturar → comparar → localizar divergência → corrigir Android → compilar/testar → capturar novamente → atualizar a matriz de paridade. Repetir até fechar todos os casos ou documentar objetivamente qualquer bloqueio externo.
