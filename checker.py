
import os
from mangaplus import MangaPlus
from mangaplus.constants import Language, Viewer

TITLE_ID = 200116
DEVICE_ID = "manga-telegram-github-actions"


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
        raise RuntimeError(
            f"Respuesta inesperada: {type(data).__name__}"
        )

    detail = data.get("titleDetailView")

    if not isinstance(detail, dict):
        print("Claves principales:", list(data.keys()))
        raise RuntimeError("No se encontró titleDetailView.")

    title_data = detail.get("title") or {}
    print("Manga:", title_data.get("name", "Nombre desconocido"))
    print("Campos del título:", list(detail.keys()))

    for list_name in ("firstChapterList", "lastChapterList"):
        items = detail.get(list_name) or []

        print(f"\n--- {list_name} ---")
        print("Tipo:", type(items).__name__)

        if isinstance(items, list):
            print("Cantidad:", len(items))

            for index, item in enumerate(items[:5]):
                print(f"Elemento {index + 1}:")

                if isinstance(item, dict):
                    print("Campos:", list(item.keys()))
                    print("Datos:", repr(item)[:1200])
                else:
                    print("Tipo:", type(item).__name__)
                    print("Datos:", repr(item)[:500])
        else:
            print("Datos:", repr(items)[:1500])

    print(
        "\nDiagnóstico terminado. "
        "No se envió ningún mensaje a Telegram."
    )


if __name__ == "__main__":
    main()
