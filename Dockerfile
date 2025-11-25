FROM python:3.12-slim

# Install system dependencies
# ffmpeg is required for video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies
# We use --system to install into the system python environment since we are in a container
RUN uv sync --frozen --no-dev

# Copy the rest of the application
COPY src/ src/
COPY README.md .

# Expose the port
EXPOSE 8000

# Run the application
# We use 'python -m uvicorn' to ensure we use the installed package context if needed,
# but calling uvicorn directly is also fine.
# We point to src.highlight_cuts.web:app (which we will create next)
CMD ["uv", "run", "uvicorn", "highlight_cuts.web:app", "--host", "0.0.0.0", "--port", "8000"]
