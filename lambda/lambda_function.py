import os
import json
import subprocess
import tempfile
import shutil
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI(title="YouTube Video Summarizer")

def stream_process(youtube_url: str):
    """Generator function that performs the work and yields the stream."""
    try:
        yield b"Starting process...\n"
        temp_dir = tempfile.mkdtemp()
        print('Process started')

        output_template = os.path.join(temp_dir, "transcript.%(ext)s")
        subtitle_path = os.path.join(temp_dir, "transcript.en.json3")
        transcript_path = os.path.join(temp_dir, "transcript.txt")

        yield b"Downloading subtitles...\n"
        yt_dlp_command = [
            'yt-dlp', '--skip-download', '--write-auto-sub',
            '--sub-format', 'json3', '--sub-lang', 'en',
            '-o', output_template, youtube_url
        ]
        
        try:
            subprocess.run(yt_dlp_command, check=True, capture_output=True, text=True)
        except FileNotFoundError:
            yield json.dumps({
                "error": "yt-dlp not found. Please install yt-dlp in your container."
            }).encode("utf-8")
            return

        if not os.path.exists(subtitle_path):
            err = json.dumps({
                "error": f"No subtitle file found. The video might not have auto-generated subtitles."
            })
            yield err.encode("utf-8")
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

        # Call OpenAI with streaming
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
                data = chunk[len(b"data: "):]
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
        yield json.dumps({
            "error": f"External command failed: {e.cmd}",
            "stdout": e.stdout if hasattr(e, 'stdout') else "",
            "stderr": e.stderr if hasattr(e, 'stderr') else "",
        }).encode("utf-8")
    except Exception as e:
        yield json.dumps({
            "error": f"Unexpected error: {str(e)}"
        }).encode("utf-8")
    finally:
        if 'temp_dir' in locals() and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
    
    yield b"\n--- End of summary ---\n"

@app.get("/")
def status():
    return {"status": "ok", "message": "YouTube Video Summarizer API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/sum", response_class=StreamingResponse)
def summarize(url: str = Query(..., description="YouTube video URL to summarize")):
    """
    Stream back status updates, transcript extraction, and LLM summary chunks.
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing `url` query parameter")

    return StreamingResponse(
        stream_process(url),
        media_type="text/plain; charset=utf-8",
    )

# For local development
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)