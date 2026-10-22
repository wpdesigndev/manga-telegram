
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

    title = detail.get("title") or {}
    print("Manga:", title.get("name", "Nombre desconocido"))
    print("Campos del título:", list(detail.keys()))

    chapters = detail.get("chapterListV2") or []

    print("\n--- chapterListV2 ---")
    print("Tipo:", type(chapters).__name__)

    if isinstance(chapters, list):
        print("Cantidad:", len(chapters))

        for index, chapter in enumerate(chapters[:20]):
            print(f"\nCapítulo/elemento {index + 1}:")

            if isinstance(chapter, dict):
                print("Campos:", list(chapter.keys()))
                print("Datos:", repr(chapter)[:2500])
            else:
                print("Tipo:", type(chapter).__name__)
                print("Datos:", repr(chapter)[:1500])
    else:
        print("Datos:", repr(chapters)[:5000])

    print("\nDiagnóstico terminado. No se envió ningún mensaje.")


if __name__ == "__main__":
    main()
