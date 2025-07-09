# TLDW (Too Long; Didn't Watch)

This project aims to provide summaries for long video content, likely leveraging YouTube transcripts.

## Development Setup

1.  **Install Dependencies:**

    ```bash
    pip install -e .
    ```

2.  **Then Run This With:**

    ```bash
    python3 src/tldw/tldw.py
    ```

## Running Tests

To run the tests:

Locally:

```bash
pytest
```

You can also run tests in the Docker container, mimicking a PyPI wheel distribution installation.

```bash
docker compose down && docker compose up -d --build && docker logs tests -f
```

## Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality and consistency before commits.

1.  **Install pre-commit:**
    If you don't have `pre-commit` installed globally, you can install it into your virtual environment:

    ```bash
    pip install pre-commit
    ```

2.  **Install the Git hooks:**
    Navigate to the root of the repository and run:

    ```bash
    pre-commit install
    ```

    This command sets up the hooks in your `.git/` directory.

3.  **Run hooks manually (optional):**
    To run all configured hooks against all files, without making a commit:
    ```bash
    pre-commit run --all-files
    ```

Now, every time you try to commit, the pre-commit hooks will automatically run. If any hook fails, the commit will be aborted, allowing you to fix the issues before committing.
