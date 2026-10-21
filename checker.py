
import os
import re
import requests

from mangaplus import MangaPlus
from mangaplus.constants import Language, Viewer

TITLE_ID = 200116
VIEWER_PREFIX = "https://mangaplus.shueisha.co.jp/viewer/"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ["TELEGRAM_CHANNEL"]
STATE_FILE = "last_chapter.txt"


def get_latest_chapter():
    print("Consultando MANGA Plus mediante su cliente de Python...")

    client = MangaPlus(
        lang=Language.SPANISH,
        clang=[Language.SPANISH],
        viewer=Viewer.VERTICAL,
    )

    try:
        response = client.getTitleDetail(title_id=TITLE_ID)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo consultar el título en MANGA Plus: {exc}"
        ) from exc

    detail = response.get("titleDetailView")
    if not isinstance(detail, dict):
        raise RuntimeError(
            "La respuesta no contiene titleDetailView. "
            f"Claves recibidas: {list(response.keys())}"
        )

    title_data = detail.get("title") or {}
    manga_name = title_data.get("name", "Boruto: Two Blue Vortex")
    print("Manga:", manga_name)

    chapters_by_id = {}

    for list_name in ("firstChapterList", "lastChapterList"):
        chapter_list = detail.get(list_name) or []

        if isinstance(chapter_list, list):
            for chapter in chapter_list:
                if not isinstance(chapter, dict):
                    continue

                chapter_id = str(chapter.get("chapterId") or "")
                if not chapter_id:
                    continue

                name = str(chapter.get("name") or "")
                subtitle = str(chapter.get("subTitle") or "")
                label = f"{name} {subtitle}".strip()

                match = re.search(
                    r"(?:cap[ií]tulo|chapter|ch\.?)\s*#?\s*(\d+(?:\.\d+)?)",
                    label,
                    re.IGNORECASE,
                )

                if not match:
                    match = re.search(
                        r"#\s*(\d+(?:\.\d+)?)",
                        label,
                    )

                if not match:
                    continue

                number_text = match.group(1)
                number = float(number_text)

                chapters_by_id[chapter_id] = {
                    "number": number,
                    "number_text": number_text,
                    "title": subtitle or name,
                    "id": chapter_id,
                }

    if not chapters_by_id:
        raise RuntimeError(
            "MANGA Plus respondió, pero no se pudieron identificar "
            "los capítulos. No se enviará ningún mensaje."
        )

    latest = max(
        chapters_by_id.values(),
        key=lambda chapter: chapter["number"],
    )

    chapter_url = VIEWER_PREFIX + latest["id"]

    print("Capítulo encontrado:", latest["number_text"])
    print("Título:", latest["title"])
    print("Enlace:", chapter_url)

    return latest["number_text"], latest["title"], chapter_url


def send_telegram(number, title, url):
    message = (
        "📖 *BORUTO - TWO BLUE VORTEX*\n\n"
        "🔥 *Nuevo capítulo disponible*\n\n"
        f"🔖 Capítulo *{number}*\n"
    )

    if title:
        message += f"📚 {title}\n"

    message += f"\n👉 [Leer en MANGA Plus en español]({url})"

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHANNEL,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    print("Telegram status:", response.status_code)
    response.raise_for_status()

    result = response.json()
    if not result.get("ok"):
        raise RuntimeError("Telegram no confirmó el envío del mensaje.")


def main():
    current, title, url = get_latest_chapter()

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            previous = file.read().strip()
    else:
        previous = ""

    print("Capítulo detectado:", current)
    print("Capítulo guardado:", previous)

    if not previous:
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            file.write(current)
        print("Primera ejecución: capítulo guardado sin publicar.")
        return

    if not re.fullmatch(r"\d+(?:\.\d+)?", previous):
        raise RuntimeError(
            "last_chapter.txt no contiene un número válido."
        )

    if float(current) <= float(previous):
        print("No hay un capítulo más reciente.")
        return

    print("Se detectó un capítulo nuevo.")
    send_telegram(current, title, url)

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        file.write(current)

    print("Mensaje enviado y capítulo guardado.")


if __name__ == "__main__":
    main()
