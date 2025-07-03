# Použi oficiálny obraz Pythonu ako základ
FROM python:3.9-slim-buster

# Nastav pracovný adresár v kontajneri
WORKDIR /app

# Skopíruj súbor requirements.txt do pracovného adresára
COPY requirements.txt .

# Nainštaluj všetky závislosti uvedené v requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Skopíruj zvyšok kódu aplikácie do pracovného adresára
COPY . .

# Exponuj port, na ktorom bude Gunicorn počúvať
# Gunicorn predvolene počúva na porte 8000
EXPOSE 8000

# Spusti aplikáciu pomocou Gunicornu
# CMD je predvolený príkaz, ktorý sa spustí pri štarte kontajnera
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]