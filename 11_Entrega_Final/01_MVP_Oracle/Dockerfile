# syntax=docker/dockerfile:1.4
# Imagem da API + carga do Retena MVP (python-oracledb modo thin: nao precisa de Instant Client).
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
# Rede corporativa com inspecao TLS (opcional): docker compose build --secret id=ca,src=<cadeia.pem>
RUN --mount=type=secret,id=ca,required=false \
    if [ -f /run/secrets/ca ]; then cat /run/secrets/ca >> /tmp/ca.pem && export PIP_CERT=/tmp/ca.pem; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY api/ api/
COPY web/ web/
COPY carga.sh verificar_mvp.py ./
ENV PYTHONIOENCODING=utf-8
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "app:app", "--app-dir", "api", "--host", "0.0.0.0", "--port", "8080"]
