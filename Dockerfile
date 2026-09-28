FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home tracker && chown -R tracker:tracker /app
USER tracker
CMD ["uvicorn", "tracker.api:app", "--host", "0.0.0.0", "--port", "8000"]
