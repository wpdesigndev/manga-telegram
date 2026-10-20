
import os
import re
import requests
from playwright.sync_api import sync_playwright

MANGA_URL = "https://mangaplus.shueisha.co.jp/titles/200116"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ["TELEGRAM_CHANNEL"]

STATE_FILE = "last_chapter.txt"


def get_latest_chapter():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Abriendo MANGA Plus...")

        page.goto(
            MANGA_URL,
            wait_until="networkidle",
            timeout=60000
        )

        page.wait_for_timeout(3000)

        text = page.locator("body").inner_text()

        print("URL actual:", page.url)
        print("URL de la página del título:", MANGA_URL)

        # Recopilar los enlaces visibles de la página.
        links = page.locator("a").evaluate_all("""
            elements => elements.map(a => ({
                text: (a.innerText || "").trim(),
                url: a.href
            }))
        """)

        print("Enlaces encontrados:", len(links))

        # Registrar enlaces del lector para investigar
        # cómo MANGA Plus identifica cada capítulo.
        viewer_links = [
            link for link in links
            if "/viewer/" in link["url"]
        ]

        print("Enlaces del lector:", len(viewer_links))

        for link in viewer_links[:30]:
            print(
                "Enlace del lector:",
                repr(link["text"]),
                link["url"]
            )

        browser.close()

    pattern = (
        r"#(\d+).*?Capítulo\s+(\d+)"
        r"(?::\s*(.*?))?(?=\n|$)"
    )

    matches = re.findall(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not matches:
        raise RuntimeError(
            "No se encontraron capítulos en MANGA Plus."
        )

    chapter_id, chapter_number, chapter_title = matches[-1]

    chapter_number = int(chapter_number)
    chapter_title = chapter_title.strip() if chapter_title else ""

    print("Capítulo encontrado:", chapter_number)
    print("Título:", chapter_title)

    # Buscar el enlace directo si está disponible.
    chapter_url = ""

    for link in links:
        url = link["url"]
        link_text = link["text"]

        if "/viewer/" not in url:
            continue

        numbers = re.findall(r"\d+", link_text)

        if str(chapter_number) in numbers:
            chapter_url = url
            break

    if not chapter_url:
        print(
            "AVISO: No se pudo identificar el enlace "
            "directo a este capítulo."
        )

    print(
        "Enlace directo:",
        chapter_url or "No encontrado"
    )

    return str(chapter_number), chapter_title, chapter_url


def send_telegram(chapter_number, chapter_title, chapter_url):
    if not chapter_url:
        raise RuntimeError(
            "No se enviará la notificación porque no "
            "se encontró el enlace directo al capítulo."
        )

    message = (
        "📖 *BORUTO - TWO BLUE VORTEX*\n\n"
        "🔥 *Nuevo capítulo disponible*\n\n"
        f"🔖 Capítulo *{chapter_number}*\n"
    )

    if chapter_title:
        message += f"📚 {chapter_title}\n"

    message += (
        "\n👉 [Leer capítulo en MANGA Plus]"
        f"({chapter_url})"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
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


def main():
    current_chapter, chapter_title, chapter_url = get_latest_chapter()

    print("Capítulo actual:", current_chapter)

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            previous_chapter = file.read().strip()
    else:
        previous_chapter = ""

    print("Capítulo guardado:", previous_chapter)

    # Primera ejecución: guardar el capítulo sin anunciarlo.
    if not previous_chapter:
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            file.write(current_chapter)

        print(
            "Primera ejecución: capítulo guardado "
            "sin enviar Telegram."
        )
        return

    # Anunciar solamente si hay un capítulo nuevo.
    if current_chapter != previous_chapter:
        print("🎉 ¡CAPÍTULO NUEVO!")

        send_telegram(
            current_chapter,
            chapter_title,
            chapter_url
        )

        with open(STATE_FILE, "w", encoding="utf-8") as file:
            file.write(current_chapter)

        print("Mensaje enviado a Telegram.")

    else:
        print("No hay capítulo nuevo.")


if __name__ == "__main__":
    main()
