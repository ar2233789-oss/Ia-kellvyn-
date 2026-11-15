# Catálogo técnico de animações — Web × Android

## Regra de comparação
A implementação web é a referência visual. Os dados abaixo foram lidos do snapshot congelado e do código Android. São parâmetros de código, não medições de vídeo nem aprovação visual. O alvo de referência é viewport lógico de 444 × 913 px; as capturas da web usam DPR 2,75, com canvas limitado internamente a DPR 2. O Android usa densidade 440 dpi (aproximadamente 2,75 px/dp).

## Parâmetros encontrados no código

| Efeito | Web (DigitalRain.tsx) | Android (RainView) | Diferença e impacto |
|---|---|---|---|
| Chuva — quantidade | round(área/6000), limite 160; cerca de 68 no viewport de referência | 68 fixas | Quantidade nominal equivalente apenas nesse tamanho; Android não escala densidade com a área |
| Chuva — movimento | 140–520 CSS px/s com dt de requestAnimationFrame | 6–23 dp por frame, atualização nominal a cada 45 ms (≈133–511 dp/s) | Velocidade média próxima; animação Android avança em passos de 45 ms |
| Chuva — trilha | Sprite vertical 4×64 com gradiente transparente→azul claro; largura desenhada de 2–3,2 px; comprimento 18–68 px | Três segmentos de linha; 1,25 dp de espessura; comprimento 18–68 dp | Perfil de transparência e continuidade diferentes; bordas da trilha podem parecer mais segmentadas |
| Chuva — opacidade | 0,15–0,55 | 0,15–0,55 em três níveis | Faixa nominal igual, distribuição espacial diferente |
| Neve — quantidade | round(área/5000), limite 160; cerca de 81 no viewport | 42 fixas | Android usa aproximadamente metade da densidade |
| Neve — movimento | 25–80 px/s; deriva senoidal de amplitude 18 px e frequência angular 0,8 rad/s | 1–3,4 dp por frame; deriva de cerca de 0,4 dp por frame, baseada na coordenada y | Trajetória e balanço não equivalentes; Android tem deriva menor e dependente da posição |
| Neve — aparência | raio 1–3,6 px; alfa 0,4–0,9 | raio 1–3,3 dp; alfa fixo próximo de 0,73 | Distribuição de tamanho semelhante, variação de opacidade menor no Android |
| Folhas — quantidade | round(área/22000), limite 160; cerca de 18 no viewport | 21 fixas (metade de particleCount) | Quantidade próxima no viewport, mas não proporcional à área |
| Folhas — movimento | 30–75 px/s; deriva senoidal com amplitude 40 px e frequência 1,2 rad/s | 1–3,4 dp por frame ×1,15; deriva de cerca de 0,8 dp por frame | Movimento lateral do Android é menor e não usa a mesma fase/onda |
| Folhas — rotação | -1,25 a +1,25 rad/s | -2,5 a +2,5 graus por frame de 45 ms | Ordem de grandeza próxima; unidade e cadência diferentes |
| Raios — intervalo inicial | 2–6 s | 2–6 s na inicialização e ao ativar dinamicamente o efeito (alinhado no patch mais recente) | Parâmetro temporal alinhado; validar a distribuição com vídeo |
| Raios — intervalo seguinte | 3–9 s | 3–9 s | Faixa nominal igual |
| Raios — descarga | inicia entre 15% e 85% da largura; termina em 45–75% da altura | mesma faixa de posição e comprimento | Geometria geral aproximada; o percurso aleatório ainda difere |
| Raios — clarão | 12% de alfa máximo, decaimento 2,2/s | 12% de alfa máximo, decaimento 2,2/s | Parâmetro nominal alinhado após patch local |
| Raios — traço | largura 1,6 px, alfa máximo 85%, glow 14 px | 1,6 dp, alfa máximo 85%, glow 14 dp | Equivalência visual ainda depende da renderização Canvas/Android |
| Composição | Chuva, neve, folhas e raios são camadas independentes; raios podem coexistir com precipitação | RainView desenha cada efeito independentemente; raios podem coexistir com chuva | Regra de composição compatível; validar capturas simultâneas |

## Fichas e testes

| ID | Elemento | Teste de captura | Critério |
|---|---|---|---|
| AN-001 | Chuva | 151 quadros por 30 s, timestamps gravados; chuva isolada | Comparar velocidade, densidade, continuidade e comprimento da trilha |
| AN-002 | Neve | 151 quadros por 30 s, neve isolada | Contar partículas por área e comparar deriva lateral |
| AN-003 | Folhas | 151 quadros por 30 s, folhas isoladas | Comparar densidade, forma, deriva e rotação |
| AN-004 | Raios | 30 s, raios isolados; repetir com chuva+raios | Comparar distribuição dos intervalos, duração do flash, posição e extensão do traço |
| AN-005 | Indicador de pensamento | Capturar início, três rótulos de 900 ms e encerramento | Alinhamento de tamanho, halo, pulso, brilho e ciclo |
| AN-006 | Microfone | Estados idle, ouvindo, permissão negada e encerramento | Pulso e estado visual equivalentes |
| AN-007 | Painéis e menus | Vídeo de abertura/fechamento e rolagem | Duração, curva, posição e sobreposição equivalentes |
| AN-008 | Menu do botão + | Abrir, fechar e selecionar cada opção | Ordem, animação, acessibilidade e hit area equivalentes |
| AN-009 | Switches | Alternar cada preferência ligada/desligada | Estado final e animação de transição |
| AN-010 | Toasts/notificações | Registrar entrada, permanência e saída | Duração e posicionamento equivalentes |
| AN-011 | Gesto de deslizar | Repetir gestos em três velocidades | Limiar e estado final equivalentes |

## Protocolo temporal
1. Registrar a mesma resolução lógica, escala, paleta, efeito habilitado e horário de início em ambas as plataformas.
2. Capturar vídeo contínuo a pelo menos 30 fps por 30 segundos; guardar os vídeos originais.
3. Extrair quadros com timestamps comuns, sem redimensionar imagens.
4. Comparar os quadros por overlay, heatmap, erro médio e percentual de pixels diferentes.
5. Para partículas aleatórias, avaliar também estatísticas de movimento e densidade; não exigir coincidência das posições aleatórias.
6. Não declarar equivalência de animação com base em um único screenshot.

## Estado
O catálogo é uma auditoria estática de código. As diferenças acima precisam ser validadas por vídeo sincronizado no AVD e, por fim, no Poco F6 físico com HyperOS. O AVD Android 15 é aproximado, não uma ROM Poco F6.
