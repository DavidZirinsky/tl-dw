import os
import json
import subprocess
import tempfile
import shutil
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import uvicorn
import re
import urllib.parse
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
        
        # Try to get transcript using YouTube Data API v3 with OAuth2 token
        try:
            # Get OAuth2 access token
            oauth_token = os.environ.get("YOUTUBE_OAUTH_TOKEN")
            if not oauth_token:
                raise Exception("YOUTUBE_OAUTH_TOKEN not set")
                
            # Build YouTube API service with OAuth token
            from google.oauth2.credentials import Credentials
            credentials = Credentials(token=oauth_token)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Get captions list
            captions_response = youtube.captions().list(
                part='snippet',
                videoId=video_id
            ).execute()
            
            if not captions_response.get('items'):
                raise Exception("No captions available for this video")
            
            # Find English captions
            caption_id = None
            for item in captions_response['items']:
                if item['snippet']['language'] == 'en':
                    caption_id = item['id']
                    break
            
            if not caption_id:
                raise Exception("No English captions found")
                
            # Download caption content
            caption_download = youtube.captions().download(
                id=caption_id,
                tfmt='srt'
            ).execute()
            
            transcript_content = caption_download.decode('utf-8')
        except Exception as e:
            yield f"Transcript API failed: {str(e)}\n".encode("utf-8")
            yield b"Falling back to yt-dlp method...\n"
            
            # Fallback to yt-dlp method
            temp_dir = tempfile.mkdtemp()
            output_template = os.path.join(temp_dir, "transcript.%(ext)s")
            subtitle_path = os.path.join(temp_dir, "transcript.en.json3")
            transcript_path = os.path.join(temp_dir, "transcript.txt")

            yt_dlp_command = [
                'yt-dlp', '--skip-download', '--write-auto-sub',
                '--sub-format', 'json3', '--sub-lang', 'en',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                '--extractor-args', 'youtube:player_client=ios,web',
                '--no-check-certificate',
                '-o', output_template, youtube_url
            ]
            subprocess.run(yt_dlp_command, check=True, capture_output=True, text=True)

            if not os.path.exists(subtitle_path):
                yield json.dumps({"error": f"No subtitle file found"}).encode("utf-8")
                return

            with open(transcript_path, "w") as f:
                subprocess.run(
                    ["jq", "-r", ".events[].segs[]?.utf8 | select(type == \"string\")", subtitle_path],
                    check=True,
                    stdout=f,
                    text=True,
                )
            
            with open(transcript_path, "r") as f:
                transcript_content = f.read()
            
            # Clean up temp directory
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)

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
    except subprocess.CalledProcessError as e:
        print(e)
        yield json.dumps(
            {
                "error": f"External command failed: {e.cmd}",
                "stdout": e.stdout,
                "stderr": e.stderr,
            }
        ).encode("utf-8")
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