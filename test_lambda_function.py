from unittest.mock import patch, MagicMock, mock_open
import json
import os
import io
import subprocess
import requests
import types

from lambda_function import lambda_handler

def open_side_effect_factory(file_mocks):
    def open_side_effect(filename, mode='r', **kwargs):
        if 'w' in mode:
            return mock_open().return_value
        elif 'r' in mode:
            if filename in file_mocks:
                return mock_open(read_data=file_mocks[filename]).return_value
            else:
                raise FileNotFoundError(f"No mock content for {filename}")
        return mock_open().return_value
    return open_side_effect

@patch('lambda_function.os.environ.get')
@patch('lambda_function.tempfile.mkdtemp')
@patch('lambda_function.shutil.rmtree')
@patch('lambda_function.os.path.exists')
@patch('lambda_function.subprocess.run')
@patch('lambda_function.requests.post')
@patch('builtins.open')
def test_successful_summary_generation(mock_open_builtin, mock_requests_post, mock_subprocess_run, mock_os_path_exists, mock_shutil_rmtree, mock_tempfile_mkdtemp, mock_environ_get):
    mock_environ_get.return_value = 'mock_openai_api_key'
    mock_tempfile_mkdtemp.return_value = '/mock/temp/dir'
    mock_os_path_exists.side_effect = lambda path: path in ['/mock/temp/dir', '/mock/temp/dir/transcript.en.json3', '/mock/temp/dir/transcript.txt']

    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout='yt-dlp output', stderr=''),
        MagicMock(returncode=0, stdout='jq output', stderr='')
    ]

    mock_json3_content = {
        "events": [
            {"segs": [{"utf8": "Hello "}]},
            {"segs": [{"utf8": "world."}]}
        ]
    }
    mock_transcript_content = "Hello world."

    file_mocks = {
        '/mock/temp/dir/transcript.en.json3': json.dumps(mock_json3_content),
        '/mock/temp/dir/transcript.txt': mock_transcript_content
    }

    mock_open_builtin.side_effect = open_side_effect_factory(file_mocks)

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    def mock_iter_lines():
        yield b'data: {"choices": [{"delta": {"content": "This is "}}]}'
        yield b'data: {"choices": [{"delta": {"content": "a test "}}]}'
        yield b'data: {"choices": [{"delta": {"content": "summary."}}]}'
        yield b'data: [DONE]'
    mock_response.iter_lines.return_value = mock_iter_lines()
    mock_requests_post.return_value = mock_response

    event = {"queryStringParameters": {"url": "https://www.youtube.com/watch?v=test_video"}}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 200
    assert 'headers' in response
    assert response['headers']['Content-Type'] == 'text/plain'
    assert isinstance(response['body'], types.GeneratorType)

    full_summary = ""
    for chunk in response['body']:
        full_summary += chunk.decode('utf-8')

    assert full_summary == "This is a test summary."

    mock_subprocess_run.assert_any_call([
        'yt-dlp', '--skip-download', '--write-auto-sub', '--sub-format', 'json3',
        '--sub-lang', 'en', '-o', '/mock/temp/dir/transcript.%(ext)s',
        'https://www.youtube.com/watch?v=test_video'
    ], check=True, capture_output=True, text=True)


    mock_requests_post.assert_called_once_with(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': 'Bearer mock_openai_api_key', 'Content-Type': 'application/json'},
        json={
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': 'Summarize the main points of this talk.'},
                {'role': 'user', 'content': mock_transcript_content}
            ],
            'stream': True
        },
        stream=True
    )

    mock_shutil_rmtree.assert_called_once_with('/mock/temp/dir')

@patch('lambda_function.os.environ.get')
@patch('lambda_function.tempfile.mkdtemp')
@patch('lambda_function.shutil.rmtree')
@patch('lambda_function.os.path.exists')
@patch('lambda_function.subprocess.run')
@patch('lambda_function.requests.post')
def test_missing_url_parameter(mock_requests_post, mock_subprocess_run, mock_os_path_exists, mock_shutil_rmtree, mock_tempfile_mkdtemp, mock_environ_get):
    event = {"queryStringParameters": {}}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 400
    assert json.loads(response['body']) == {'error': 'Missing "url" query parameter.'}
    mock_subprocess_run.assert_not_called()
    mock_requests_post.assert_not_called()
    mock_shutil_rmtree.assert_not_called()

@patch('lambda_function.os.environ.get')
@patch('lambda_function.tempfile.mkdtemp')
@patch('lambda_function.shutil.rmtree')
@patch('lambda_function.os.path.exists')
@patch('lambda_function.subprocess.run')
@patch('lambda_function.requests.post')
def test_yt_dlp_failure_subtitle_not_found(mock_requests_post, mock_subprocess_run, mock_os_path_exists, mock_shutil_rmtree, mock_tempfile_mkdtemp, mock_environ_get):
    mock_environ_get.return_value = 'mock_openai_api_key'
    mock_tempfile_mkdtemp.return_value = '/mock/temp/dir'
    mock_os_path_exists.side_effect = lambda path: path in ['/mock/temp/dir', '/mock/temp/dir/transcript.txt']

    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout='yt-dlp output', stderr='')

    event = {"queryStringParameters": {"url": "https://www.youtube.com/watch?v=test_video"}}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 500
    assert json.loads(response['body']) == {'error': 'Subtitle file not found at /mock/temp/dir/transcript.en.json3. Check if subtitles are available for the video.'}
    mock_requests_post.assert_not_called()
    mock_shutil_rmtree.assert_called_once_with('/mock/temp/dir')

@patch('lambda_function.os.environ.get')
@patch('lambda_function.tempfile.mkdtemp')
@patch('lambda_function.shutil.rmtree')
@patch('lambda_function.os.path.exists')
@patch('lambda_function.subprocess.run')
@patch('lambda_function.requests.post')
def test_yt_dlp_command_failure(mock_requests_post, mock_subprocess_run, mock_os_path_exists, mock_shutil_rmtree, mock_tempfile_mkdtemp, mock_environ_get):
    mock_environ_get.return_value = 'mock_openai_api_key'
    mock_tempfile_mkdtemp.return_value = '/mock/temp/dir'
    mock_os_path_exists.return_value = True

    mock_error = subprocess.CalledProcessError(1, cmd='yt-dlp')
    mock_error.stdout = 'some stdout'
    mock_error.stderr = 'yt-dlp error'
    mock_subprocess_run.side_effect = mock_error

    event = {"queryStringParameters": {"url": "https://www.youtube.com/watch?v=test_video"}}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 500
    error_body = json.loads(response['body'])
    assert 'External command failed: yt-dlp' in error_body['error']
    assert error_body['stdout'] == 'some stdout'
    assert error_body['stderr'] == 'yt-dlp error'
    mock_requests_post.assert_not_called()
    mock_shutil_rmtree.assert_called_once_with('/mock/temp/dir')


@patch('lambda_function.os.environ.get')
@patch('lambda_function.tempfile.mkdtemp')
@patch('lambda_function.shutil.rmtree')
@patch('lambda_function.os.path.exists')
@patch('lambda_function.subprocess.run')
@patch('lambda_function.requests.post')
@patch('builtins.open')
def test_missing_openai_api_key(mock_open_builtin, mock_requests_post, mock_subprocess_run, mock_os_path_exists, mock_shutil_rmtree, mock_tempfile_mkdtemp, mock_environ_get):
    mock_environ_get.return_value = None
    mock_tempfile_mkdtemp.return_value = '/mock/temp/dir'
    mock_os_path_exists.side_effect = lambda path: path in ['/mock/temp/dir', '/mock/temp/dir/transcript.en.json3', '/mock/temp/dir/transcript.txt']

    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout='yt-dlp output', stderr=''),
        MagicMock(returncode=0, stdout='jq output', stderr='')
    ]

    mock_json3_content = {
        "events": [
            {"segs": [{"utf8": "Hello "}]},
            {"segs": [{"utf8": "world."}]}
        ]
    }
    mock_transcript_content = "Hello world."

    file_mocks = {
        '/mock/temp/dir/transcript.en.json3': json.dumps(mock_json3_content),
        '/mock/temp/dir/transcript.txt': mock_transcript_content
    }

    mock_open_builtin.side_effect = open_side_effect_factory(file_mocks)

    event = {"queryStringParameters": {"url": "https://www.youtube.com/watch?v=test_video"}}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 500
    assert json.loads(response['body']) == {'error': 'OPENAI_API_KEY not set in environment variables.'}
    mock_requests_post.assert_not_called()
    mock_shutil_rmtree.assert_called_once_with('/mock/temp/dir')

@patch('lambda_function.os.environ.get')
@patch('lambda_function.tempfile.mkdtemp')
@patch('lambda_function.shutil.rmtree')
@patch('lambda_function.os.path.exists')
@patch('lambda_function.subprocess.run')
@patch('lambda_function.requests.post')
@patch('builtins.open')
def test_openai_api_failure(mock_open_builtin, mock_requests_post, mock_subprocess_run, mock_os_path_exists, mock_shutil_rmtree, mock_tempfile_mkdtemp, mock_environ_get):
    mock_environ_get.return_value = 'mock_openai_api_key'
    mock_tempfile_mkdtemp.return_value = '/mock/temp/dir'
    mock_os_path_exists.side_effect = lambda path: path in ['/mock/temp/dir', '/mock/temp/dir/transcript.en.json3', '/mock/temp/dir/transcript.txt']

    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout='yt-dlp output', stderr=''),
        MagicMock(returncode=0, stdout='jq output', stderr='')
    ]

    mock_json3_content = {
        "events": [
            {"segs": [{"utf8": "Hello "}]},
            {"segs": [{"utf8": "world."}]}
        ]
    }
    mock_transcript_content = "Hello world."

    file_mocks = {
        '/mock/temp/dir/transcript.en.json3': json.dumps(mock_json3_content),
        '/mock/temp/dir/transcript.txt': mock_transcript_content
    }

    mock_open_builtin.side_effect = open_side_effect_factory(file_mocks)

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Client Error: Unauthorized")
    mock_requests_post.return_value = mock_response

    event = {"queryStringParameters": {"url": "https://www.youtube.com/watch?v=test_video"}}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 500
    assert json.loads(response['body']) == {'error': '401 Client Error: Unauthorized'}
    mock_shutil_rmtree.assert_called_once_with('/mock/temp/dir')

@patch('lambda_function.os.environ.get')
@patch('lambda_function.tempfile.mkdtemp')
@patch('lambda_function.shutil.rmtree')
@patch('lambda_function.os.path.exists')
@patch('lambda_function.subprocess.run')
@patch('lambda_function.requests.post')
@patch('builtins.open')
def test_empty_transcript_content(mock_open_builtin, mock_requests_post, mock_subprocess_run, mock_os_path_exists, mock_shutil_rmtree, mock_tempfile_mkdtemp, mock_environ_get):
    mock_environ_get.return_value = 'mock_openai_api_key'
    mock_tempfile_mkdtemp.return_value = '/mock/temp/dir'
    mock_os_path_exists.side_effect = lambda path: path in ['/mock/temp/dir', '/mock/temp/dir/transcript.en.json3', '/mock/temp/dir/transcript.txt']

    mock_subprocess_run.side_effect = [
        MagicMock(returncode=0, stdout='yt-dlp output', stderr=''),
        MagicMock(returncode=0, stdout='', stderr='')
    ]

    mock_json3_content = {
        "events": [
            {"segs": [{"utf8": ""}]},
        ]
    }
    mock_transcript_content = ""

    file_mocks = {
        '/mock/temp/dir/transcript.en.json3': json.dumps(mock_json3_content),
        '/mock/temp/dir/transcript.txt': mock_transcript_content
    }

    mock_open_builtin.side_effect = open_side_effect_factory(file_mocks)

    event = {"queryStringParameters": {"url": "https://www.youtube.com/watch?v=test_video"}}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 500
    assert json.loads(response['body']) == {'error': 'Could not extract any text from the subtitles.'}
    mock_requests_post.assert_not_called()
    mock_shutil_rmtree.assert_called_once_with('/mock/temp/dir')
