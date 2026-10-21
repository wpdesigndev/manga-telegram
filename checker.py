
import os
import re
import uuid
import requests

API_URL = "https://jumpg-webapi.tokyo-cdn.com/api/title_detailV3"
TITLE_ID = "200116"
VIEWER_PREFIX = "https://mangaplus.shueisha.co.jp/viewer/"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ["TELEGRAM_CHANNEL"]
STATE_FILE = "last_chapter.txt"


def get_latest_chapter():
    print("Consultando la API de MANGA Plus...")

    params = {
        "title_id": TITLE_ID,
        "lang": "eng",
        "clang": "spa",
        "country_code": "US",
        "format": "json",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/141.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Origin": "https://mangaplus.shueisha.co.jp",
        "Referer": "https://mangaplus.shueisha.co.jp/",
        "Session-Token": str(uuid.uuid4()),
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=headers,
        timeout=30,
    )

    print("Estado HTTP de la API:", response.status_code)
    print("URL consultada:", response.url)

    if response.status_code == 403:
        raise RuntimeError(
            "MANGA Plus ha rechazado la petición (403). "
            "Los encabezados y parámetros adicionales no han "
            "resuelto el bloqueo. No se publicará nada."
        )

    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "La respuesta no es JSON. Tipo de contenido: "
            f"{response.headers.get('Content-Type')}. "
            f"Inicio de respuesta: {response.text[:300]}"
        )

    success = data.get("success")
    if not isinstance(success, dict):
        raise RuntimeError(
            "La API no devolvió un objeto 'success'. "
            f"Respuesta: {str(data)[:1000]}"
        )

    detail = success.get("titleDetailView")
    if not isinstance(detail, dict):
        raise RuntimeError(
            "No se encontró titleDetailView en la respuesta. "
            f"Claves recibidas: {list(success.keys())}"
        )

    title = detail.get("title") or {}
    print("Manga:", title.get("name", "Nombre no disponible"))

    chapters_by_id = {}

    for list_name in ("firstChapterList", "lastChapterList"):
        chapter_list = detail.get(list_name) or []

        if isinstance(chapter_list, list):
            for chapter in chapter_list:
                if not isinstance(chapter, dict):
                    continue

                chapter_id = str(chapter.get("chapterId") or "")
                if chapter_id:
                    chapters_by_id[chapter_id] = chapter

    candidates = []

    for chapter_id, chapter in chapters_by_id.items():
        name = str(chapter.get("name") or "")
        subtitle = str(chapter.get("subTitle") or "")
        label = f"{name} {subtitle}".strip()

        match = re.search(
            r"(?:cap[ií]tulo|chapter|ch\.?)\s*#?\s*(\d+)",
            label,
            re.IGNORECASE,
        )

        if not match:
            match = re.search(r"#\s*(\d+)", label)

        if not match:
            continue

        candidates.append({
            "number": int(match.group(1)),
            "id": chapter_id,
            "title": subtitle or name,
        })

    if not candidates:
        print(
            "Campos recibidos:",
            list(detail.keys()),
        )
        print(
            "Listas de capítulos:",
            {
                key: len(detail.get(key) or [])
                for key in ("firstChapterList", "lastChapterList")
            },
        )
        raise RuntimeError(
            "La respuesta llegó, pero no se pudieron identificar "
            "los números de los capítulos."
        )

    latest = max(candidates, key=lambda item: item["number"])

    chapter_number = str(latest["number"])
    chapter_title = latest["title"]
    chapter_url = VIEWER_PREFIX + latest["id"]

    print("Capítulo encontrado:", chapter_number)
    print("Título:", chapter_title)
    print("Enlace directo:", chapter_url)

    return chapter_number, chapter_title, chapter_url


def send_telegram(number, title, url):
    message = (
        "📖 *BORUTO - TWO BLUE VORTEX*\n\n"
        "🔥 *Nuevo capítulo disponible*\n\n"
        f"🔖 Capítulo *{number}*\n"
    )

    if title:
        message += f"📚 {title}\n"

    message += (
        "\n👉 [Leer en MANGA Plus en español]"
        f"({url})"
    )

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
        raise RuntimeError(
            "Telegram no confirmó el envío del mensaje."
        )


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
            "last_chapter.txt no contiene un número válido."
        )

    if int(current) <= int(previous):
        print("No hay un capítulo numéricamente más reciente.")
        return

    print("Se detectó un capítulo nuevo.")
    send_telegram(current, title, url)

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        file.write(current)

    print("Mensaje enviado y capítulo guardado.")


if __name__ == "__main__":
    main()
