# Matriz de paridade — Kellvyn Web × Android

## Revisões congeladas
- Snapshot base: commit `8e6d4456f0ceec57a65f5a078c26277e447d68bf` do repositório principal.
- Código web de referência: `snapshot/src/components/kellvyn/` e `snapshot/src/styles.css`.
- Código Android candidato: `snapshot/android/`.
- O ajuste de raios neste laboratório é experimental e isolado. A interface web permanece intocada.
- Viewport alvo da comparação: 444 × 913 dp/CSS px; Chromium DPR 2,75; AVD 1220 × 2712 px/440 dpi. AVD não equivale a hardware/HyperOS Poco F6.

## Diferenças de implementação verificadas no código
| Área | Web (referência) | Android (antes do patch local) | Alvo de paridade |
|---|---|---|---|
| Chuva | Sprite 4×64 com gradiente; requestAnimationFrame; 140–520 px/s; trilhas 18–68 px | 68 trilhas em três segmentos; Handler a cada 45 ms | Gradiente contínuo, velocidade e fluidez equivalentes |
| Neve | Quantidade por área/5000, máximo 160; deriva lateral senoidal | 42 partículas; deslocamento reduzido | Quantidade, balanço e fase |
| Folhas | Área/22000; oscilação lateral de 40 px; rotação contínua | 21 folhas; oscilação menor, rotação por frame | Densidade e trajetória |
| Raios | Clarão 12%; glow 14 px; traço 1,6 px; fim em 45–75% da altura; primeiro intervalo 2–6 s; seguintes 3–9 s | Clarão 3,5%; glow 5 dp; traço 1,35 dp; fim 40–52% | Patch experimental aplicado no Android: 12%, 14 dp, 1,6 dp, 45–75%, temporização alinhada |
| Indicador de pensamento | Três estados textuais e animação CSS | Indicador nativo ajustado no candidato PR #19 | Estado, tamanho, halo e duração durante streaming |
| Microfone | Pulso CSS enquanto ouve | Estado nativo separado | Idle, ouvindo, permissão/erro e encerramento |
| Painéis | Sheet HTML com transições CSS | Dialog nativo | Altura, margens, sobreposição, rolagem e transições |

Valores da coluna web são parâmetros encontrados no código, não medições finais de screenshots. O patch de raios precisa de captura no AVD e no aparelho físico antes de ser aprovado.

## Casos de teste obrigatórios
| ID | Caso | Evidência |
|---|---|---|
| UI-001 | Tela principal vazia | PNG web/native + overlay + heatmap |
| UI-002 | Mensagem longa e ações | PNG sincronizado + árvore de controles |
| UI-003 | Histórico aberto/fechado | PNG + controles acessíveis |
| UI-004 | Menu + aberto | PNG + inventário de opções |
| UI-005 | Acesso à Web off/on/off | preferência persistida + PNG |
| UI-006 | Configurações topo/meio/fim | screenshots de cada rolagem |
| UI-007 | Dez paletas predefinidas | HEX persistido + screenshots |
| UI-008 | Cores HEX personalizadas | acento/fundo/texto + screenshot |
| FX-001 | Chuva | sequência temporal sincronizada |
| FX-002 | Chuva + raios | sequência temporal sincronizada |
| FX-003 | Neve | sequência temporal sincronizada |
| FX-004 | Folhas | sequência temporal sincronizada |
| FX-005 | Alternância repetida de efeitos | sem travamento, crash ou estado perdido |
| FX-006 | Trocar cor durante streaming | resposta continua e tela não congela |
| IN-001 | Indicador de pensamento | início, três estados e fim |
| IN-002 | Microfone | idle, ouvindo, permissão/erro e parar |
| IN-003 | Campo e envio | uma mensagem, sem duplicação |
| IN-004 | Arquivo/anexo | seleção, preview, remoção e envio |
| SYS-001 | Teclado e barras do sistema | composer sem sobreposição |
| SYS-002 | Morte do processo/restauração | conversa e preferências coerentes |

## Aprovação
1. Mesma resolução lógica, escala, conteúdo, paleta e estado interativo.
2. Não redimensionar capturas para esconder diferenças; dimensão incompatível invalida o par.
3. Gerar originais, overlay 50%, diff amplificado, heatmap e JSON.
4. Animação requer quadros nomeados/timestamps equivalentes; um único PNG não prova equivalência.
5. Tolerância é declarada por caso; abaixo da tolerância significa “dentro do limite”, não “pixel-perfect”.
6. Aprovação final do Poco F6 exige validação no aparelho físico.
