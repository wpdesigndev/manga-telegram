
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

        print("Abriendo MANGA Plus en español...")

        page.goto(
            MANGA_URL,
            wait_until="networkidle",
            timeout=60000
        )

        page.wait_for_timeout(3000)
        text = page.locator("body").inner_text()

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
            browser.close()
            raise RuntimeError(
                "No se encontraron capítulos en MANGA Plus."
            )

        chapter_id, chapter_number, chapter_title = matches[-1]
        chapter_number = int(chapter_number)
        chapter_title = (
            chapter_title.strip() if chapter_title else ""
        )

        print("Capítulo encontrado:", chapter_number)
        print("Título:", chapter_title)

        chapter_url = ""

        # Intentar abrir la tarjeta del capítulo.
        if chapter_title:
            try:
                target = page.get_by_text(
                    chapter_title,
                    exact=False
                ).last

                target.click(timeout=10000)
                page.wait_for_timeout(3000)

                if "/viewer/" in page.url:
                    chapter_url = page.url
                else:
                    print(
                        "La página no navegó directamente "
                        "al lector del capítulo."
                    )

            except Exception as error:
                print(
                    "No se pudo abrir la tarjeta del capítulo:",
                    str(error)
                )

        # Comprobar si la URL es del lector oficial.
        if chapter_url and not chapter_url.startswith(
            "https://mangaplus.shueisha.co.jp/viewer/"
        ):
            chapter_url = ""

        print(
            "Enlace directo:",
            chapter_url or "No encontrado"
        )

        browser.close()

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
        "\n👉 [Leer capítulo en español en MANGA Plus]"
        f"({chapter_url})"
    )

    url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

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
    current_chapter, chapter_title, chapter_url = (
        get_latest_chapter()
    )

    print("Capítulo actual:", current_chapter)

    if os.path.exists(STATE_FILE):
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            previous_chapter = file.read().strip()
    else:
        previous_chapter = ""

    print("Capítulo guardado:", previous_chapter)

    # Primera ejecución: guardar sin publicar.
    if not previous_chapter:
        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(current_chapter)

        print(
            "Primera ejecución: capítulo guardado "
            "sin enviar Telegram."
        )
        return

    # Publicar solamente si el capítulo cambió.
    if current_chapter != previous_chapter:
        print("🎉 ¡CAPÍTULO NUEVO!")

        send_telegram(
            current_chapter,
            chapter_title,
            chapter_url
        )

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(current_chapter)

        print("Mensaje enviado a Telegram.")

    else:
        print("No hay capítulo nuevo.")


if __name__ == "__main__":
    main()
