default: lint test

sync:
    uv sync --all-extras --dev

lint: check format
check:
    uv run ruff check
format:
    uv run ruff format

test:
    uv run ptyest

docker tag:
    docker buildx build --tag {{ tag }} .

run:
    uv run main.py
