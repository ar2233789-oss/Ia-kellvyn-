# Protocolo de comparação visual

1. Registrar versão/commit da web e do Android.
2. Fixar resolução lógica, densidade, orientação, tema, paleta e estado da interface.
3. Capturar o mesmo estado nos dois sistemas; aguardar estabilização de fontes e animações.
4. Comparar dimensões antes dos pixels. Não redimensionar silenciosamente.
5. Gerar imagem lado a lado, overlay com transparência e mapa de diferenças.
6. Informar percentual de pixels divergentes, limiar por canal e regiões afetadas.
7. Para animações, gravar sequências com a mesma duração e taxa de quadros; comparar quadros alinhados no tempo e métricas de movimento.
8. Guardar arquivos originais, configuração, logs e relatório JSON em `evidence/<run-id>/`.

## Critérios
- Igualdade exata: 0% de pixels diferentes, quando renderização e ambiente permitem.
- Tolerância: qualquer limite diferente de zero precisa ser declarado por teste; nunca chamar de pixel-perfect.
- Dimensões diferentes, captura ausente ou estado incompatível: teste inválido/falha, nunca aprovação.
- Um detector de movimento ou flash não comprova que a animação está semanticamente correta; revisão visual continua obrigatória.
