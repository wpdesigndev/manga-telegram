
import os
import re
import time
import requests
from playwright.sync_api import sync_playwright

MANGA_URL = "https://mangaplus.shueisha.co.jp/titles/200116"
VIEWER_PREFIX = "https://mangaplus.shueisha.co.jp/viewer/"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ["TELEGRAM_CHANNEL"]
STATE_FILE = "last_chapter.txt"


def get_latest_chapter():
    last_error = "No se encontraron capítulos."

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        try:
            for attempt in range(1, 4):
                page = browser.new_page(
                    locale="es-ES",
                    accept_downloads=False
                )

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

                    page.wait_for_timeout(10000)

                    print("Título de la página:", page.title())
                    print("URL final:", page.url)

                    body_text = page.locator("body").inner_text()
                    print("Texto visible:", body_text[:2000])

                    # Buscar números de capítulos en el texto visible.
                    patterns = [
                        r"#\s*(\d+)\s*[\r\n]+.*?Capítulo\s+\d+",
                        r"Capítulo\s+(\d+)\s*[:：\-]?\s*([^\r\n]*)",
                        r"第\s*(\d+)\s*話"
                    ]

                    matches = []

                    for pattern in patterns:
                        found = re.findall(
                            pattern,
                            body_text,
                            flags=re.IGNORECASE
                        )
                        if found:
                            matches = found
                            break

                    if not matches:
                        last_error = (
                            "La página cargó, pero no se "
                            "encontraron capítulos en el texto visible."
                        )
                        print(last_error)
                        print("HTML recibido:", page.content()[:3000])

                        if attempt < 3:
                            page.close()
                            time.sleep(5)
                            continue

                        break

                    # Normalizar el resultado de los patrones.
                    last_match = matches[-1]

                    if isinstance(last_match, tuple):
                        chapter_number = int(last_match[0])
                        chapter_title = (
                            last_match[1].strip()
                            if len(last_match) > 1
                            else ""
                        )
                    else:
                        chapter_number = int(last_match)
                        chapter_title = ""

                    print("Capítulo encontrado:", chapter_number)
                    print("Título:", chapter_title or "(sin título)")

                    # Buscar enlaces del lector de capítulos.
                    chapter_url = ""

                    links = page.locator("a[href*='/viewer/']")
                    for index in range(links.count()):
                        href = links.nth(index).get_attribute("href")
                        if href and "/viewer/" in href:
                            if href.startswith("/"):
                                chapter_url = (
                                    "https://mangaplus.shueisha.co.jp"
                                    + href
                                )
                            elif href.startswith("http"):
                                chapter_url = href
                            break

                    # Si no aparece un enlace directo en el HTML,
                    # intentar abrir la tarjeta del capítulo.
                    if not chapter_url and chapter_title:
                        try:
                            target = page.get_by_text(
                                chapter_title,
                                exact=False
                            ).last

                            target.click(timeout=10000)
                            page.wait_for_timeout(3000)

                            if page.url.startswith(VIEWER_PREFIX):
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

                    if not chapter_url:
                        last_error = (
                            "Se encontró un posible capítulo, "
                            "pero no se pudo verificar su enlace directo."
                        )
                        print(last_error)

                        if attempt < 3:
                            page.close()
                            time.sleep(5)
                            continue

                        break

                    return (
                        str(chapter_number),
                        chapter_title,
                        chapter_url
                    )

                except Exception as error:
                    last_error = str(error)
                    print("Error de lectura:", last_error)

                    if attempt < 3:
                        time.sleep(5)

                finally:
                    try:
                        page.close()
                    except Exception:
                        pass

            raise RuntimeError(
                "No se pudo comprobar el último capítulo después "
                f"de 3 intentos. Detalle: {last_error}"
            )

        finally:
            browser.close()


def send_telegram(chapter_number, chapter_title, chapter_url):
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

    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram no confirmó el envío: {result}"
        )


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
            "Primera ejecución: capítulo guardado sin enviar Telegram."
        )
        return

    if current_chapter == previous_chapter:
        print("No hay capítulo nuevo.")
        return

    print("¡Posible capítulo nuevo!")

    # Enviar solo cuando el enlace directo ya se haya verificado.
    send_telegram(
        current_chapter,
        chapter_title,
        chapter_url
    )

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        file.write(current_chapter)

    print("Mensaje enviado y capítulo guardado.")


if __name__ == "__main__":
    main()
