default: lint test

sync:
    uv sync --all-extras --dev

lint: check format
check:
    uv run ruff check
format:
    uv run ruff format

test:
    uv run python3 -m ptyest

docker tag:
    docker buildx build --tag {{ tag }} .

run:
    uv run main.py
