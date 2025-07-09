import os
import json
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import uvicorn
import re
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI()

def stream_process(youtube_url: str):
    """Generator function that performs the work and yields the stream."""
    try:
        yield b"Starting process...\n"
        
        # Extract video ID from URL
        video_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)', youtube_url)
        if not video_id_match:
            yield json.dumps({"error": "Invalid YouTube URL"}).encode("utf-8")
            return
        
        video_id = video_id_match.group(1)
        yield f"Extracting video ID: {video_id}\n".encode("utf-8")

        yield b"Downloading transcript...\n"
        proxy_pass = os.environ.get('PROXY_USER_PASS')
        
      
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            transcript_content = ' '.join([entry['text'] for entry in transcript_list])
        except Exception as e:
            yield f"Failed to get transcript: {str(e)}\n".encode("utf-8")
            yield json.dumps({"error": f"Could not retrieve transcript: {str(e)}"}).encode("utf-8")
            return

        if not transcript_content.strip():
            yield json.dumps({"error": "Could not extract any text from the video"}).encode("utf-8")
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
        print('96')
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
        print('113')
    except Exception as e:
        print(f"Unexpected error: {e}")
        yield json.dumps({"error": f"Unexpected error: {str(e)}"}).encode("utf-8")
    print('126')
    yield b"\n--- End of summary ---\n"

@app.get("/")
def status():
    return {"status": "ok", "service": "tldw"}


@app.get("/sum", response_class=StreamingResponse)
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

# for local dev
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)