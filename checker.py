
import os
import re
import json
import requests

API_URL = "https://jumpg-webapi.tokyo-cdn.com/api/title_detailV3"
TITLE_ID = "200116"
VIEWER_PREFIX = "https://mangaplus.shueisha.co.jp/viewer/"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ["TELEGRAM_CHANNEL"]
STATE_FILE = "last_chapter.txt"


def get_latest_chapter():
    print("Consultando la API de MANGA Plus...")

    response = requests.get(
        API_URL,
        params={"title_id": TITLE_ID, "format": "json"},
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://mangaplus.shueisha.co.jp",
            "Referer": "https://mangaplus.shueisha.co.jp/",
        },
        timeout=30,
    )

    print("Estado HTTP de la API:", response.status_code)
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "La API no devolvió JSON. Respuesta: "
            + response.text[:500]
        )

    if "success" not in data:
        raise RuntimeError(
            "La API no confirmó la consulta: "
            + json.dumps(data, ensure_ascii=False)[:1000]
        )

    detail = data["success"].get("titleDetailView")
    if not detail:
        raise RuntimeError(
            "La respuesta no contiene titleDetailView: "
            + json.dumps(data, ensure_ascii=False)[:1000]
        )

    title = detail.get("title", {})
    print("Manga:", title.get("name", "Nombre no disponible"))
    print("Idioma informado por la API:", title.get("language"))

    chapters = []
    for key in ("firstChapterList", "lastChapterList"):
        chapters.extend(detail.get(key) or [])

    # Evitar capítulos repetidos si aparecen en ambas listas.
    unique = {}
    for chapter in chapters:
        chapter_id = str(chapter.get("chapterId", ""))
        if chapter_id:
            unique[chapter_id] = chapter

    candidates = []

    for chapter_id, chapter in unique.items():
        name = str(chapter.get("name") or "")
        subtitle = str(chapter.get("subTitle") or "")
        label = f"{name} {subtitle}".strip()

        # Buscar el número del capítulo en sus nombres.
        patterns = [
            r"(?:cap[ií]tulo|chapter|ch\.?)\s*#?\s*(\d+)",
            r"#\s*(\d+)",
        ]

        number = None
        for pattern in patterns:
            match = re.search(pattern, label, re.IGNORECASE)
            if match:
                number = int(match.group(1))
                break

        if number is not None:
            candidates.append({
                "number": number,
                "id": chapter_id,
                "title": subtitle or name,
                "label": label,
            })

    if not candidates:
        print(
            "Capítulos recibidos:",
            json.dumps(chapters, ensure_ascii=False)[:3000]
        )
        raise RuntimeError(
            "La API respondió, pero no pude identificar "
            "números de capítulos."
        )

    latest = max(candidates, key=lambda item: item["number"])

    print("Capítulo identificado:", latest["number"])
    print("Título:", latest["title"])
    print("ID del capítulo:", latest["id"])

    return (
        str(latest["number"]),
        latest["title"],
        VIEWER_PREFIX + latest["id"],
    )


def send_telegram(number, title, url):
    message = (
        "📖 *BORUTO - TWO BLUE VORTEX*\n\n"
        "🔥 *Nuevo capítulo disponible*\n\n"
        f"🔖 Capítulo *{number}*\n"
    )

    if title:
        message += f"📚 {title}\n"

    message += f"\n👉 [Leer en MANGA Plus]({url})"

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
        raise RuntimeError("Telegram no confirmó el envío.")


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

    if not previous.isdigit():
        raise RuntimeError(
            "El archivo last_chapter.txt no contiene "
            "un número de capítulo válido."
        )

    if int(current) <= int(previous):
        print("No hay un capítulo numéricamente más reciente.")
        return

    print("Posible capítulo nuevo. Enviando a Telegram...")
    send_telegram(current, title, url)

    # Guardar el estado solamente después de confirmar el envío.
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        file.write(current)

    print("Mensaje enviado y capítulo guardado.")


if __name__ == "__main__":
    main()
