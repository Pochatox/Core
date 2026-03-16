FROM python:3.12-slim

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

COPY . .

COPY start.sh .
RUN chmod +x start.sh

CMD ["sh", "./start.sh"]
