FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# ✅ Pievienots --timeout 120, lai izvairītos no worker timeout kļūdām
CMD ["gunicorn", "--timeout", "120", "--bind", "0.0.0.0:8080", "main:app"]
