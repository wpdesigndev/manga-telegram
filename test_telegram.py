
import os
import requests

token = os.environ["TELEGRAM_BOT_TOKEN"]
channel = os.environ["TELEGRAM_CHANNEL"]

url = f"https://api.telegram.org/bot{token}/sendMessage"

message = (
    "📢 ¡Nuevo capítulo disponible!\n\n"
    "📚 Boruto: Two Blue Vortex\n"
    "📖 Capítulo 38\n\n"
    "🔗 Leer capítulo en MANGA Plus:\n"
    "https://mangaplus.shueisha.co.jp/titles/100269\n\n"
    "🤖 Aviso automático de MANGA Plus"
)

response = requests.post(
    url,
    data={
        "chat_id": channel,
        "text": message,
    },
    timeout=30,
)

print(response.status_code)
print(response.text)

response.raise_for_status()
