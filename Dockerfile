FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
ENV PRODUCTS_ROOT=/data/products
VOLUME ["/data/products"]
EXPOSE 8000 8001
CMD ["gerador-web"]
