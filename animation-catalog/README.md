# Catálogo de animações

Cada animação deve ter uma ficha própria com: identificador, componente, gatilho, estados inicial/final, duração, atraso, easing/curva, repetição, direção, amplitude, cores/opacidade, posição, dependências de viewport e critério visual de aprovação.

## Itens já identificados para auditoria
| ID | Elemento | Diferença conhecida a verificar |
|---|---|---|
| AN-001 | Chuva | Web usa trilha contínua com gradiente e requestAnimationFrame; Android usa três segmentos e atualização periódica de 45 ms. |
| AN-002 | Neve | Densidade e balanço lateral diferem entre web e Android. |
| AN-003 | Folhas | Quantidade, oscilação horizontal e rotação diferem. |
| AN-004 | Raios | Clarão, brilho e extensão da descarga diferem; medir em condições equivalentes. |
| AN-005 | Indicador de pensamento | Textos alternam em intervalos de 900 ms; pulso/brilho CSS não está reproduzido no Android. |
| AN-006 | Microfone | Pulso animado da web ausente no Android. |
| AN-007 | Painéis e menus | Web usa transições CSS; Android usa janelas nativas com transições diferentes. |
| AN-008 | Menu do botão + | Capturar abertura, fechamento, sequência e sobreposição. |
| AN-009 | Switches | Comparar estado, interpolação e feedback tátil/visual. |
| AN-010 | Toasts/notificações | Comparar entrada, permanência, saída e posicionamento. |
| AN-011 | Gesto de deslizar | Comparar limiar, velocidade, continuidade e estado final. |

Os valores acima são observações preliminares herdadas da auditoria anterior, não medições finais. Devem ser revalidados com arquivos de referência e capturas sincronizadas.
