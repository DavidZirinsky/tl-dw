import json
import os
import subprocess
import tempfile
import shutil

import requests

def lambda_handler(event, context):
    """
    AWS Lambda function to summarize a YouTube video using its subtitles,
    with streaming response to the frontend.

    Expects a GET request with a 'url' query parameter for the YouTube video.
    """
    try:
        query_params = event.get('queryStringParameters', {})
        youtube_url = query_params.get('url')

        if not youtube_url:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing "url" query parameter.'})
            }

        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, 'transcript.%(ext)s')
        subtitle_path = os.path.join(temp_dir, 'transcript.en.json3')
        transcript_path = os.path.join(temp_dir, 'transcript.txt')

        try:
            # Download the English json3 subtitle using yt-dlp
            # yt-dlp needs to be available in the Lambda environment (e.g., via a layer)
            yt_dlp_command = [
                'yt-dlp',
                '--skip-download',
                '--write-auto-sub',
                '--sub-format', 'json3',
                '--sub-lang', 'en',
                '-o', output_template,
                youtube_url
            ]
            subprocess.run(yt_dlp_command, check=True, capture_output=True, text=True)

            if not os.path.exists(subtitle_path):
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': f'Subtitle file not found at {subtitle_path}. Check if subtitles are available for the video.'})
                }

            # Extract the text from the json3 subtitle file using jq
            # jq also needs to be available in the Lambda environment (e.g., via a layer)
            jq_command = [
                'jq',
                '-r',
                '.events[].segs[]?.utf8 | select(type == "string")',
                subtitle_path
            ]
            with open(transcript_path, 'w') as f:
                subprocess.run(jq_command, check=True, stdout=f, text=True)

            with open(transcript_path, 'r') as f:
                transcript_content = f.read()

            if not transcript_content.strip():
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'Could not extract any text from the subtitles.'})
                }

            # --- Streaming LLM API Call --- 
            llm_api_key = os.environ.get('OPENAI_API_KEY')
            if not llm_api_key:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'OPENAI_API_KEY not set in environment variables.'})
                }

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
                'stream': True # <--- IMPORTANT: Enable streaming
            }

            # Make the streaming request to OpenAI
            llm_response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                stream=True # <--- IMPORTANT: Keep the connection open for streaming
            )
            llm_response.raise_for_status()

            # API Gateway expects a specific format for streaming responses.
            # The 'body' must be a generator that yields bytes.
            # Each yielded chunk will be sent as a separate part of the HTTP response.
            def generate_summary_chunks():
                for chunk in llm_response.iter_lines():
                    if chunk:
                        # OpenAI's streaming response sends data lines prefixed with "data: "
                        # and a final "[DONE]" message.
                        if chunk.startswith(b'data: '):
                            json_chunk = chunk[len(b'data: '):]
                            if json_chunk == b'[DONE]':
                                break
                            try:
                                data = json.loads(json_chunk)
                                # Extract the content from the chunk
                                content = data['choices'][0]['delta'].get('content', '')
                                if content:
                                    yield content.encode('utf-8') # Yield as bytes
                            except json.JSONDecodeError:
                                # Handle malformed JSON chunks if necessary
                                pass
                # Ensure the stream is properly closed
                llm_response.close()

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/plain', # Or application/json if you're sending JSON chunks
                    'Transfer-Encoding': 'chunked' # API Gateway handles this automatically with streaming
                },
                'body': generate_summary_chunks() # Pass the generator function
            }

        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    except subprocess.CalledProcessError as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'External command failed: {e.cmd}',
                'stdout': e.stdout,
                'stderr': e.stderr
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
