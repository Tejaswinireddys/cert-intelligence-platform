FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/src

COPY pyproject.toml ./
COPY src ./src
COPY playbooks ./playbooks

RUN pip install --no-cache-dir -e .

RUN mkdir -p /data
ENV CIP_DATABASE_URL=sqlite:////data/cip.db

EXPOSE 8000
CMD ["uvicorn", "cip.app:app", "--host", "0.0.0.0", "--port", "8000"]
