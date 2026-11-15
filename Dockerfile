FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.js ./
COPY frontend ./frontend
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY pipeline ./pipeline
COPY FINAL ./FINAL
COPY scripts/build_final_data.py ./scripts/build_final_data.py
COPY data/sample.csv data/provenance.json ./data/
COPY data/ingest.py ./data/
COPY --from=frontend /app/dist ./dist
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
