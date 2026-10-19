# ---------- Stage 1: builder ----------
# Installs Python packages into a virtual environment.
FROM python:3.10-slim AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements first so this layer is cached
# and code changes don't trigger a full reinstall
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---------- Stage 2: runtime ----------
# Starts from a clean image and copies in only the installed packages.
# pip caches and build leftovers from stage 1 are left behind.
FROM python:3.10-slim AS runtime

LABEL maintainer="Gaurav Choughule" \
      description="MLOps Docker Lab 1 - breast cancer classifier (train + serve)"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Run as a normal user instead of root (security best practice)
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/model \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser src/ .

USER appuser

# Default training settings (can be overridden with -e at runtime)
ENV MODEL_TYPE=logreg \
    TEST_SIZE=0.2 \
    RANDOM_STATE=42

EXPOSE 8000

# Default: train the model and exit (same behaviour as the original lab)
CMD ["python", "train.py"]
