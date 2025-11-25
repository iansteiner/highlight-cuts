import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def test_dockerfile_exists():
    dockerfile = BASE_DIR / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text()
    assert "FROM python:3.12-slim" in content
    assert "RUN uv sync" in content
    assert "EXPOSE 8000" in content

def test_docker_compose_exists():
    compose = BASE_DIR / "docker-compose.yml"
    assert compose.exists()
    content = compose.read_text()
    assert "services:" in content
    assert "highlight-cuts-web" in content
    assert "8000:8000" in content
