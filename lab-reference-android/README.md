# Kellvyn Web Reference — laboratório

Este módulo é um APK auxiliar e temporário de QA. Ele abre a interface web servida localmente dentro do Android WebView para que a referência visual e o APK nativo sejam renderizados no mesmo AVD e na mesma sessão do sistema.

- Pacote: `com.kellvyn.labreference`
- Endereço de teste: `http://127.0.0.1:4173/` encaminhado pelo `adb reverse`
- Estados suportados: `main`, `settings`, `gold-settings`, `gold-main`
- Relatório de estado: tag Logcat `KellvynWebViewLab`
- Dispositivo usado: AVD `PocoF6Virtual` configurado pelo script `scripts/prepare_poco_f6_virtual.sh`

**Não faz parte do app Kellvyn.** O pacote, código e permissões deste módulo não são copiados para `snapshot/android` nem publicados no APK de distribuição. As capturas e comparações ficam apenas como artefatos temporários do GitHub Actions; não são commitadas.
