# CutClipAI Project Instructions

## Project Structure

Follow the project structure strictly. Do not move files. Do not rename directories.

## Code Organization

All code must be typed and documented.

### Directory Responsibilities

- **routers** - API routing only, no business logic
- **services** - Core business logic implementation
- **workers** - Background tasks using Celery
- **bot** - Telegram bot handlers and logic
- **utils** - Technical helper functions
- **core** - System setup and configuration

## Key Principles

1. Routers contain no business logic - they only handle HTTP requests/responses
2. Services implement core functionality
3. Workers run background tasks asynchronously
4. Bot handlers implement Telegram interaction flows
5. Utils provide reusable technical utilities
6. Core modules handle system-wide configuration

## Development Guidelines

- Use type hints everywhere
- Write docstrings in English only
- Follow PEP 8 style guide
- Keep functions small and focused
- No ORM - Redis is used for storage
- All video operations use ffmpeg

