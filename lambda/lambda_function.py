import json
import os
import subprocess
import tempfile
import shutil
import requests

def stream_process(youtube_url):
    print('in stream_process')
    """Generator function that performs the work and yields the stream."""
    try:
        yield b"Starting process...\n"
        temp_dir = tempfile.mkdtemp()
        print('14')
        try:
            output_template = os.path.join(temp_dir, 'transcript.%(ext)s')
            subtitle_path = os.path.join(temp_dir, 'transcript.en.json3')
            transcript_path = os.path.join(temp_dir, 'transcript.txt')

            yield b"Downloading subtitles...\n"
            yt_dlp_command = [
                'yt-dlp', '--skip-download', '--write-auto-sub',
                '--sub-format', 'json3', '--sub-lang', 'en',
                '-o', output_template, youtube_url
            ]
            subprocess.run(yt_dlp_command, check=True, capture_output=True, text=True)
            print('27')
            if not os.path.exists(subtitle_path):
                yield json.dumps({'error': f'Subtitle file not found at {subtitle_path}.'}).encode('utf-8')
                return

            yield b"Extracting transcript...\n"
            jq_command = [
                'jq', '-r', '.events[].segs[]?.utf8 | select(type == "string")',
                subtitle_path
            ]
            print('37')
            with open(transcript_path, 'w') as f:
                subprocess.run(jq_command, check=True, stdout=f, text=True)

            with open(transcript_path, 'r') as f:
                transcript_content = f.read()

            if not transcript_content.strip():
                yield json.dumps({'error': 'Could not extract any text from the subtitles.'}).encode('utf-8')
                return

            print('48')
            yield b"Generating summary...\n"
            llm_api_key = os.environ.get('OPENAI_API_KEY')
            if not llm_api_key:
                yield json.dumps({'error': 'OPENAI_API_KEY not set.'}).encode('utf-8')
                return

            headers = {
                'Authorization': f'Bearer {llm_api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': 'Summarize the main points of this talk.'},
                    {'role': 'user', 'content': transcript_content}
                ],
                'stream': True
            }

            llm_response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers, json=payload, stream=True
            )
            llm_response.raise_for_status()
            print('73')
            for chunk in llm_response.iter_lines():
                if chunk and chunk.startswith(b'data: '):
                    json_chunk = chunk[len(b'data: '):]
                    if json_chunk == b'[DONE]':
                        break
                    try:
                        data = json.loads(json_chunk)
                        content = data['choices'][0]['delta'].get('content', '')
                        if content:
                            yield content.encode('utf-8')
                    except json.JSONDecodeError:
                        pass
            llm_response.close()

        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        yield b"\n--- End of summary ---\n"

    except subprocess.CalledProcessError as e:
        yield json.dumps({
            'error': f'External command failed: {e.cmd}',
            'stdout': e.stdout,
            'stderr': e.stderr
        }).encode('utf-8')
    except Exception as e:
        yield json.dumps({'error': str(e)}).encode('utf-8')

from aws_lambda_powertools.event_handler.api_gateway import stream_response

@stream_response
def lambda_handler(event, context):
    print('starting')
    """
    AWS Lambda function to summarize a YouTube video using its subtitles,
    with streaming response to the frontend.
    """
    query_params = event.get('queryStringParameters', {})
    youtube_url = query_params.get('url') if query_params else None

    if not youtube_url:
        # This will now correctly return a 404
        context.fail("Missing 'url' query parameter.")

    return stream_process(youtube_url)
