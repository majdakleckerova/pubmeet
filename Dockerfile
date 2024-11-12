# Základní obraz s Pythonem
FROM python:3.9-slim

# Nastavení pracovního adresáře v kontejneru
WORKDIR /app

# Zkopírování requirements.txt a instalace závislostí
COPY requirements.txt .
RUN pip install -r requirements.txt

# Zkopírování celého projektu
COPY . .

# Exponování portu
EXPOSE 5000

# Spuštění aplikace
CMD ["flask", "run", "--host=0.0.0.0"]