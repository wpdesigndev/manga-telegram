
import os
import re
import time
import requests
from playwright.sync_api import sync_playwright

MANGA_URL = "https://mangaplus.shueisha.co.jp/titles/200116"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ["TELEGRAM_CHANNEL"]

STATE_FILE = "last_chapter.txt"


def get_latest_chapter():
    last_error = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        try:
            for attempt in range(1, 4):
                page = browser.new_page()

                try:
                    print(
                        f"Abriendo MANGA Plus en español "
                        f"(intento {attempt}/3)..."
                    )

                    page.goto(
                        MANGA_URL,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    # Dar tiempo a que la aplicación cargue.
                    page.wait_for_timeout(10000)

                    print("Título de la página:", page.title())
print("URL final:", page.url)
print("Estado del documento:", page.locator("body").count())
print("HTML recibido:", page.content()[:3000])
print("Errores de página:", page.locator("body").inner_text()[:500])

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
                        last_error = (
                            "La página cargó, pero no se "
                            "encontraron capítulos."
                        )
                        print(last_error)
                        print("URL actual:", page.url)
                        print("Texto visible:", text[:1500])

                        page.close()

                        if attempt < 3:
                            time.sleep(5)
                            continue

                        break

                    _, chapter_number, chapter_title = matches[-1]

                    chapter_number = int(chapter_number)
                    chapter_title = (
                        chapter_title.strip()
                        if chapter_title else ""
                    )

                    print("Capítulo encontrado:", chapter_number)
                    print("Título:", chapter_title)

                    # Obtener la URL directa del lector en español.
                    chapter_url = ""

                    if chapter_title:
                        try:
                            target = page.get_by_text(
                                chapter_title,
                                exact=False
                            ).last

                            target.click(timeout=10000)
                            page.wait_for_timeout(3000)

                            if (
                                page.url.startswith(
                                    "https://mangaplus.shueisha.co.jp/viewer/"
                                )
                            ):
                                chapter_url = page.url

                        except Exception as error:
                            print(
                                "No se pudo abrir la tarjeta:",
                                str(error)
                            )

                    print(
                        "Enlace directo:",
                        chapter_url or "No encontrado"
                    )

                    page.close()

                    return (
                        str(chapter_number),
                        chapter_title,
                        chapter_url
                    )

                except Exception as error:
                    last_error = str(error)
                    print("Error de lectura:", last_error)

                    try:
                        page.close()
                    except Exception:
                        pass

                    if attempt < 3:
                        time.sleep(5)

            raise RuntimeError(
                "No se pudo leer MANGA Plus después de "
                f"3 intentos. Último error: {last_error}"
            )

        finally:
            browser.close()


def send_telegram(chapter_number, chapter_title, chapter_url):
    if not chapter_url:
        raise RuntimeError(
            "No se enviará el mensaje porque falta "
            "el enlace directo al capítulo."
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


def main():
    current_chapter, chapter_title, chapter_url = (
        get_latest_chapter()
    )

    print("Capítulo actual:", current_chapter)

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            previous_chapter = file.read().strip()
    else:
        previous_chapter = ""

    print("Capítulo guardado:", previous_chapter)

    if not previous_chapter:
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            file.write(current_chapter)

        print(
            "Primera ejecución: capítulo guardado "
            "sin enviar Telegram."
        )
        return

    if current_chapter != previous_chapter:
        print("¡CAPÍTULO NUEVO!")

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
