.PHONY: setup run dev install deploy test clean format type-check

# Set the Python version from cookiecutter or default to 3.10
PYTHON_VERSION := 3.11

# Setup with uv
setup:
	# Check if uv is installed, install if not
	@which uv >/dev/null || pip install uv
	# Create a virtual environment
	uv venv
	# Install dependencies with development extras
	uv pip install -e ".[dev]"
	@echo "✅ Environment setup complete. Activate it with 'source .venv/bin/activate' (Unix/macOS) or '.venv\\Scripts\activate' (Windows)"

# Run the server directly
run:
	python -m mcp_server.server

# Run in development mode with MCP inspector
dev:
	mcp dev mcp_server.server

# Install in Claude Desktop
install:
	mcp install mcp_server.server

# Run tests
test:
	pytest

# Format code with black and isort
format:
	black mcp_server
	isort mcp_server

# Check types with mypy
type-check:
	mypy mcp_server

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Docker build
docker-build:
	docker build -t mcp-server:latest .

# Run with Docker
docker-run:
	docker run -p 8000:8000 mcp-server:latest