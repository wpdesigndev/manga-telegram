# Manga Telegram · aviso de capítulos nuevos

Avisa por Telegram cuando sale un capítulo nuevo de **Boruto: Two Blue Vortex** en español en
[MANGA Plus](https://mangaplus.shueisha.co.jp/titles/200116).

## Cómo funciona

- GitHub Actions ejecuta `checker.py` cada 15 minutos (workflow **MANGA Plus Checker**).
- El script consulta MANGA Plus (librería [MangaPlus](https://github.com/hyugogirubato/MangaPlus)), busca el capítulo con
  el número más alto y lo compara con el guardado en `last_chapter.txt`.
- Si hay uno nuevo, manda al canal de Telegram el título, el número, la descripción y el enlace para leerlo, y solo
  después de que Telegram confirme el envío actualiza `last_chapter.txt` (el workflow lo sube al repo).
- Si no hay capítulo nuevo, no hace nada. Si `last_chapter.txt` falta o no tiene un número, se detiene sin avisar, para
  no mandar avisos equivocados.

## Archivos

| Archivo | Qué es |
|---|---|
| `checker.py` | Comprueba MANGA Plus y manda el aviso |
| `last_chapter.txt` | Último capítulo avisado (lo actualiza el workflow) |
| `test_telegram.py` | Manda un mensaje de prueba para comprobar que el bot y el canal funcionan |
| `.github/workflows/telegram-test.yml` | Workflow **MANGA Plus Checker** (cada 15 minutos) |
| `.github/workflows/test-telegram.yml` | Workflow **Test Telegram Delivery** (solo a mano) |

## Configuración

Repo › Settings › Secrets and variables › Actions:

| Secreto | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token del bot (de @BotFather) |
| `TELEGRAM_CHANNEL` | canal o chat donde avisar (p. ej. `@micanal` o su id numérico); el bot debe ser administrador del canal |

## Probar

- **Que llegan los mensajes:** Actions › **Test Telegram Delivery** › Run workflow.
- **Una comprobación ahora:** Actions › **MANGA Plus Checker** › Run workflow.

## Otro manga

Cambia en `checker.py` `TITLE_ID`, `MANGA_TITLE` y `MANGA_URL` (el id es el número de la dirección del manga en MANGA
Plus) y pon en `last_chapter.txt` el último capítulo que ya salió.
