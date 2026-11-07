# Agent Hive web (Cloud Run). Build context = repo root.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY web/requirements.txt web/requirements.txt
RUN pip install --no-cache-dir -r web/requirements.txt
COPY agenthive agenthive
COPY web web
# The catalog (with the four building blocks per agent) is generated from the same source the agents are built from.
RUN python web/build_catalog.py && rm -rf agenthive/grounding/corpus
RUN useradd --create-home --uid 10001 hive && chown -R hive /app
USER hive
CMD ["sh", "-c", "uvicorn web.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
