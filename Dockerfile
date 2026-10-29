FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sanjay_pilot ./sanjay_pilot
EXPOSE 10000
CMD ["sh","-c","uvicorn sanjay_pilot.app:app --host 0.0.0.0 --port ${PORT:-10000}"]
