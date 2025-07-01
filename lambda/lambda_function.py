import os
import json
import subprocess
import tempfile
import shutil
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()

def stream_process(youtube_url: str):
    """Generator function that performs the work and yields the stream."""
    try:
        yield b"Starting process...\n"
        temp_dir = tempfile.mkdtemp()

        output_template = os.path.join(temp_dir, "transcript.%(ext)s")
        subtitle_path = os.path.join(temp_dir, "transcript.en.json3")
        transcript_path = os.path.join(temp_dir, "transcript.txt")

        yield b"Downloading subtitles...\n"
        subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                "--write-auto-sub",
                "--sub-format",
                "json3",
                "--sub-lang",
                "en",
                "-o",
                output_template,
                youtube_url,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        if not os.path.exists(subtitle_path):
            yield json.dumps(
                {"error": f"Subtitle file not found at {subtitle_path}."}
            ).encode("utf-8")
            return

        yield b"Extracting transcript...\n"
        with open(transcript_path, "w") as f:
            subprocess.run(
                ["jq", "-r", ".events[].segs[]?.utf8 | select(type == \"string\")", subtitle_path],
                check=True,
                stdout=f,
                text=True,
            )

        with open(transcript_path, "r") as f:
            transcript_content = f.read()

        if not transcript_content.strip():
            yield json.dumps(
                {"error": "Could not extract any text from the subtitles."}
            ).encode("utf-8")
            return

        yield b"Generating summary...\n"
        llm_api_key = os.environ.get("OPENAI_API_KEY")
        if not llm_api_key:
            yield json.dumps({"error": "OPENAI_API_KEY not set."}).encode("utf-8")
            return

        # call OpenAI with streaming
        headers = {
            "Authorization": f"Bearer {llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Summarize the main points of this talk."},
                {"role": "user", "content": transcript_content},
            ],
            "stream": True,
        }
        llm_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
        )
        llm_response.raise_for_status()

        for chunk in llm_response.iter_lines():
            if chunk and chunk.startswith(b"data: "):
                data = chunk[len(b"data: ") :]
                if data == b"[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    content = obj["choices"][0]["delta"].get("content", "")
                    if content:
                        yield content.encode("utf-8")
                except json.JSONDecodeError:
                    continue

        llm_response.close()

    except subprocess.CalledProcessError as e:
        yield json.dumps(
            {
                "error": f"External command failed: {e.cmd}",
                "stdout": e.stdout,
                "stderr": e.stderr,
            }
        ).encode("utf-8")
    finally:
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)

    yield b"\n--- End of summary ---\n"


@app.get("/", response_class=StreamingResponse)
def summarize(url: str = Query(..., description="YouTube video URL to summarize")):
    """
    Stream back status updates, transcript extraction, and LLM summary chunks.
    """
    # Validate URL presence
    if not url:
        raise HTTPException(status_code=400, detail="Missing `url` query parameter")

    # Wrap our generator in a StreamingResponse
    return StreamingResponse(
        stream_process(url),
        media_type="text/plain; charset=utf-8",
    )


if __name__ == "__main__":
    # Local dev with Uvicorn


    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)