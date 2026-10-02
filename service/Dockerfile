FROM python:3.11-slim AS build
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser
WORKDIR /app
COPY --from=build /install /usr/local
COPY app ./app
USER 10001
EXPOSE 8000
ENV APP_VERSION=v1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
