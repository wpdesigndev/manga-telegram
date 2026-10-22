
import os
import re
import requests
from pathlib import Path

from mangaplus import MangaPlus
from mangaplus.constants import Language, Viewer


TITLE_ID = 200116
DEVICE_ID = "manga-telegram-github-actions"
STATE_FILE = Path("last_chapter.txt")
MANGA_TITLE = "Boruto: Two Blue Vortex"
MANGA_URL = "https://mangaplus.shueisha.co.jp/titles/200116"


def get_chapter_number(chapter):
    """Extrae el número del capítulo desde los datos de MANGA Plus."""
    name = str(chapter.get("name") or "")
    subtitle = str(chapter.get("subTitle") or "")

    match = re.search(r"#\s*(\d+)", name)
    if not match:
        match = re.search(
            r"cap[ií]tulo\s+(\d+)",
            subtitle,
            re.IGNORECASE,
        )

    return int(match.group(1)) if match else None


def send_telegram_message(message):
    """Envía el aviso y comprueba que Telegram lo haya aceptado."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel = os.environ["TELEGRAM_CHANNEL"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": channel,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram no confirmó el envío: {result}"
        )

    print("Mensaje enviado correctamente a Telegram.")


def main():
    print("Conectando con MANGA Plus...")

    client = MangaPlus(
        lang=Language.SPANISH,
        clang=[Language.SPANISH],
        viewer=Viewer.VERTICAL,
    )

    print("Registrando el dispositivo...")
    client.register(device_id=DEVICE_ID)

    print("Consultando los detalles del manga...")
    data = client.getTitleDetail(title_id=TITLE_ID)

    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inesperada de MANGA Plus.")

    detail = data.get("titleDetailView")
    if not isinstance(detail, dict):
        raise RuntimeError("No se encontró titleDetailView.")

    chapters = detail.get("chapterListV2")

    if not isinstance(chapters, list) or not chapters:
        raise RuntimeError(
            "MANGA Plus no devolvió una lista de capítulos válida."
        )

    available_chapters = []

    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue

        number = get_chapter_number(chapter)
        chapter_id = chapter.get("chapterId")

        if number is not None and chapter_id is not None:
            available_chapters.append((number, chapter))

    if not available_chapters:
        raise RuntimeError(
            "No se pudieron identificar los números e IDs de los capítulos."
        )

    latest_number, latest_chapter = max(
        available_chapters,
        key=lambda item: item[0],
    )

    chapter_id = latest_chapter["chapterId"]
    subtitle = str(latest_chapter.get("subTitle") or "").strip()

    print(f"Último capítulo encontrado: {latest_number}")
    print(f"ID del capítulo: {chapter_id}")
    print(f"Descripción: {subtitle}")

    if not STATE_FILE.exists():
        raise RuntimeError(
            "No existe last_chapter.txt. "
            "No se enviará ningún aviso ni se inicializará el estado "
            "automáticamente para evitar notificaciones incorrectas."
        )

    saved_value = STATE_FILE.read_text(encoding="utf-8").strip()

    if not saved_value.isdigit():
        raise RuntimeError(
            "last_chapter.txt no contiene un número de capítulo válido."
        )

    last_number = int(saved_value)
    print(f"Último capítulo registrado: {last_number}")

    if latest_number <= last_number:
        print("No hay capítulos nuevos. No se enviará ningún mensaje.")
        return

    chapter_url = (
        f"https://mangaplus.shueisha.co.jp/viewer/{chapter_id}"
    )

    chapter_description = (
        f"\n{subtitle}" if subtitle else ""
    )

    message = (
        "📢 ¡Nuevo capítulo disponible!\n\n"
        f"📚 {MANGA_TITLE}\n"
        f"📖 Capítulo {latest_number}"
        f"{chapter_description}\n\n"
        "🔗 Leer capítulo en español:\n"
        f"{chapter_url}\n\n"
        "🤖 Aviso automático de MANGA Plus"
    )

    print("Se detectó un capítulo nuevo. Enviando aviso...")
    send_telegram_message(message)

    # Solo actualiza el estado después de confirmar el envío.
    STATE_FILE.write_text(
        f"{latest_number}\n",
        encoding="utf-8",
    )

    print(f"Estado actualizado al capítulo {latest_number}.")


if __name__ == "__main__":
    main()
