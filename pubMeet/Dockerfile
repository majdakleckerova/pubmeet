# Použití oficiálního Python image
FROM python:3.9-slim

# Nastavení pracovního adresáře
WORKDIR /app

# Zkopírování requirements.txt a instalace závislostí
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Zkopírování celé aplikace
COPY . .

# Nastavení proměnných prostředí
ENV FLASK_APP=app
ENV FLASK_ENV=development

# Exponování portu Flask aplikace
EXPOSE 5000

# Spuštění aplikace
CMD ["flask", "run", "--host=0.0.0.0"]