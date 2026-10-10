# Docker Official Image mirror: avoid Docker Hub's shared-builder pull limits.
FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    ORBITTRACE_PUBLIC_MODE=1
WORKDIR /app
COPY pyproject.toml ./
COPY backend ./backend
COPY src ./src
RUN python -m pip install --no-cache-dir -r backend/requirements.production.txt \
    && python -m pip install --no-cache-dir --no-deps . \
    && useradd --create-home --uid 10001 orbittrace
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/api/health', timeout=4)"
CMD ["python", "-I", "-m", "app.core.server"]
