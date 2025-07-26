# TLDW (Too Long; Didn't Watch)

[![PyPI version](https://badge.fury.io/py/tldw.svg)](https://pypi.org/project/tldw/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test](https://github.com/DavidZirinsky/tl-dw/actions/workflows/test.yml/badge.svg)](https://github.com/DavidZirinsky/tl-dw/actions/workflows/test.yml)

A Python package that instantly summarizes YouTube videos using AI. Get the key points from any video without watching it!

<p align="center">
  <img width="600" src="https://github.com/user-attachments/assets/7686bdcb-b3d9-4155-b9cc-15462f9f5fd2">
</p>

## ✨ Features

- 🎥 **YouTube Video Summarization**: Extract transcripts and generate concise summaries
- 🤖 **OpenAI GPT Integration**: Powered by GPT-4o-mini for high-quality summaries
- 🎨 **Beautiful CLI Output**: Colorized terminal output with ASCII art
- 🔄 **Streaming Response**: Real-time summary generation
- 🐍 **Simple Python API**: Easy to integrate into your projects

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Installation

Install from PyPI:

```bash
pip install tldw
```

From source:

```bash
git clone git@github.com:DavidZirinsky/tl-dw.git
cd tl-dw/
python3 -m pip install .
```

### Usage

```python
from tldw import tldw
import os

# Initialize with your OpenAI API key
summary = tldw(os.environ.get('OPENAI_API_KEY'))

# Summarize a YouTube video
summary.summarize('https://www.youtube.com/watch?v=LCEmiRjPEtQ')
```

### Using a Proxy

If you need to use a proxy to fetch the YouTube transcript, you can pass a `proxies` dictionary. This is useful for environments with network restrictions.

```python
from tldw import tldw
import os

# Your proxy URL
proxy_url = "http://user:pass@host:port"

# Initialize with proxy settings
summary = tldw(
    os.environ.get('OPENAI_API_KEY'),
    proxies={'http': proxy_url, 'https': proxy_url}
)

# Summarize a YouTube video through the proxy
summary.summarize('https://www.youtube.com/watch?v=LCEmiRjPEtQ')
```

**Note**: The proxy is only used for fetching the YouTube transcript, not for requests to the OpenAI API.

## 📝 Example Output

```
  ________    ____ _       __
 /_  __/ /   / __ \ |     / /
  / / / /   / / / / | /| / /
 / / / /___/ /_/ /| |/ |/ /
/_/ /_____/_____/ |__/|__/


Summarizing video: https://www.youtube.com/watch?v=LCEmiRjPEtQ

--- Summary ---

In his talk, Andre Carpathy, former director of AI at Tesla, discusses the evolving
nature of software in the era of AI, particularly emphasizing the transition from
traditional coding (Software 1.0) to an AI-driven paradigm (Software 2.0 and 3.0).
He categorizes Software 1.0 as conventional code that directly instructs computers,
while Software 2.0 encompasses neural networks where the focus is on tuning data
sets instead of writing explicit code. He introduces Software 3.0, which involves
large language models (LLMs) that can be prompted in natural language, making
programming more accessible to non-coders.

[...continued summary...]

--- End of Summary ---
```

## ❓ Troubleshooting

### Common Issues

**"OpenAI API key is required" Error**

- Make sure your OpenAI API key is set in the environment variable `OPENAI_API_KEY`
- Verify your API key is valid and has sufficient credits

**"Invalid YouTube URL provided" Error**

- Ensure the URL is a valid YouTube video URL
- Supported formats: `https://www.youtube.com/watch?v=VIDEO_ID` or `https://youtu.be/VIDEO_ID`

**"Failed to get transcript" Error**

- The video may not have English captions/transcripts available
- Some videos may have restricted access to transcripts
- Try with a different video that has confirmed English captions
- If you are behind a firewall, you may need to use a proxy (see `Using a Proxy` section)

**API Rate Limiting**

- If you encounter rate limiting, wait a few moments before trying again
- Consider upgrading your OpenAI API plan for higher rate limits

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 🛠️ Development Setup

1.  **Install Dependencies:**

    ```bash
    pip install -e .
    ```

2.  **Then Run This With:**

    ```bash
    python3 src/tldw/tldw.py
    ```

## 🧪 Running Tests

To run the tests:

Locally:

```bash
pytest
```

You can also run tests in the Docker container, mimicking a PyPI wheel distribution installation.

```bash
docker compose down && docker compose up -d --build && docker logs tests -f
```

## 🤝 Pre-commit Hooks

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

## 📦 Packaging for PyPI and Test PyPi

For PyPI:

**Build and Upload:**

```bash
pip install build twine
python3 -m build
python3 -m twine upload  dist/*
```

For Test PyPi:

**Build and Upload:**

```bash
pip install build twine
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```

**Test PyPi Installation:**

```bash
pip install --index-url https://test.pypi.org/simple/ \
--extra-index-url https://pypi.org/simple \
tldw==1.0.3
```
