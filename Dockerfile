# Используем публичный базовый образ Python с uv
ARG BASE_IMAGE=ghcr.io/astral-sh/uv:python3.12-bookworm
FROM ${BASE_IMAGE} AS base

LABEL maintainer="dimkablin"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    uv sync --no-install-project --all-extras

COPY . /app