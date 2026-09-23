FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -c requirements.lock . && useradd --create-home app && mkdir /app/data && chown app:app /app/data
USER app
ENV XPESQUISA_DATA_DIR=/app/data
EXPOSE 8765
CMD ["xpesquisa", "serve", "--host", "0.0.0.0"]
