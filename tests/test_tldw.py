from unittest.mock import MagicMock, patch

import pytest
import requests

from tldw.tldw import VideoSummarizer as tldw

YOUTUBE_URL = "https://www.youtube.com/watch?v=test_video"


#    Tests the successful generation of a summary.
@patch("tldw.tldw.YouTubeTranscriptApi.get_transcript")
@patch("tldw.tldw.requests.post")
def test_successful_summary_generation(mock_requests_post, mock_get_transcript):

    # Mock get_transcript to return list of dicts (as the real API does)
    mock_get_transcript.return_value = [{"text": "Hello"}, {"text": "world."}]

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "This is "}}]}',
        b'data: {"choices": [{"delta": {"content": "a test "}}]}',
        b'data: {"choices": [{"delta": {"content": "summary."}}]}',
        b"data: [DONE]",
    ]
    mock_requests_post.return_value.__enter__.return_value = mock_response

    summarizer = tldw(openai_api_key="fake_key")

    summary_generator = summarizer.stream_summary(YOUTUBE_URL)
    full_summary = "".join(list(summary_generator))

    assert full_summary == "This is a test summary."
    mock_get_transcript.assert_called_once_with("test_video", languages=["en"])
    mock_requests_post.assert_called_once()


def test_init_requires_api_key():
    with pytest.raises(ValueError, match="OpenAI API key is required."):
        tldw(openai_api_key="")


def test_invalid_youtube_url():
    summarizer = tldw(openai_api_key="fake_key")
    result = list(summarizer.stream_summary("not_a_youtube_url"))
    assert len(result) == 1
    assert "Error: Invalid YouTube URL provided." in result[0]


#  Tests that a RuntimeError is raised when the transcript cannot be fetched.
@patch("tldw.tldw.YouTubeTranscriptApi")
def test_transcript_fetch_failure(mock_yt_api_class):
    mock_yt_api_instance = MagicMock()
    mock_yt_api_instance.get_transcript.side_effect = Exception(
        "Failed to fetch transcript"
    )
    mock_yt_api_instance.list_transcripts.side_effect = Exception(
        "Failed to fetch transcript"
    )
    mock_yt_api_class.return_value = mock_yt_api_instance

    summarizer = tldw(openai_api_key="fake_key")

    result = list(summarizer.stream_summary(YOUTUBE_URL))

    assert len(result) == 1
    assert "Error: Failed to get transcript: Failed to fetch transcript" in result[0]


#  Tests that a ValueError is raised for an empty transcript.
@patch("tldw.tldw.YouTubeTranscriptApi.get_transcript")
def test_empty_transcript(mock_get_transcript):
    mock_get_transcript.return_value = [{"text": " "}]
    summarizer = tldw(openai_api_key="fake_key")

    result = list(summarizer.stream_summary(YOUTUBE_URL))

    assert len(result) == 1
    assert (
        "Error: Could not extract any text from the video (transcript is empty)."
        in result[0]
    )


# Tests that an error is yielded when the OpenAI API returns an HTTP error.
@patch("tldw.tldw.YouTubeTranscriptApi.get_transcript")
@patch("tldw.tldw.requests.post")
def test_openai_api_http_error(mock_requests_post, mock_get_transcript):
    mock_entry = MagicMock()
    mock_entry.text = "Test transcript."
    mock_get_transcript.return_value = [{"text": "Hello"}, {"text": "world."}]

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "401 Unauthorized"
    )
    mock_requests_post.return_value.__enter__.return_value = mock_response

    summarizer = tldw(openai_api_key="fake_key")
    result = list(summarizer.stream_summary(YOUTUBE_URL))

    assert len(result) == 1
    assert "Error: 401 Unauthorized" in result[0]


# Tests that malformed JSON from the OpenAI stream is handled gracefully.
@patch("tldw.tldw.YouTubeTranscriptApi.get_transcript")
@patch("tldw.tldw.requests.post")
def test_malformed_json_from_openai(mock_requests_post, mock_get_transcript):
    mock_get_transcript.return_value = [{"text": "Test transcript."}]

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "Valid "}}]}',
        b"data: not-a-json-object",
        b'data: {"choices": [{"delta": {"content": "chunk."}}]}',
        b"data: [DONE]",
    ]
    mock_requests_post.return_value.__enter__.return_value = mock_response

    summarizer = tldw(openai_api_key="fake_key")
    full_summary = "".join(list(summarizer.stream_summary(YOUTUBE_URL)))

    assert full_summary == "Valid chunk."


# Tests Russian video with English subtitles available through translation
@patch("tldw.tldw.YouTubeTranscriptApi")
@patch("tldw.tldw.requests.post")
def test_russian_video_with_english_translation(mock_requests_post, mock_yt_api_class):
    # Mock the YouTube Transcript API instance
    mock_yt_api_instance = MagicMock()
    mock_yt_api_class.return_value = mock_yt_api_instance

    # First call to get_transcript with English fails (no English subtitles)
    mock_yt_api_instance.get_transcript.side_effect = Exception("No English transcript")

    # Mock the transcript list and translation flow
    mock_transcript_list = MagicMock()
    mock_translatable_transcript = MagicMock()
    mock_translatable_transcript.is_translatable = True
    mock_translated_transcript = MagicMock()

    # Mock the fetched snippets from translated transcript
    mock_snippet1 = MagicMock()
    mock_snippet1.text = "This is a Russian video"
    mock_snippet2 = MagicMock()
    mock_snippet2.text = "translated to English."
    mock_translated_transcript.fetch.return_value = [mock_snippet1, mock_snippet2]

    mock_translatable_transcript.translate.return_value = mock_translated_transcript
    mock_transcript_list.__iter__.return_value = iter([mock_translatable_transcript])
    mock_yt_api_instance.list_transcripts.return_value = mock_transcript_list

    # Mock OpenAI API response
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "Summary of "}}]}',
        b'data: {"choices": [{"delta": {"content": "Russian video."}}]}',
        b"data: [DONE]",
    ]
    mock_requests_post.return_value.__enter__.return_value = mock_response

    summarizer = tldw(openai_api_key="fake_key")
    summary_generator = summarizer.stream_summary(YOUTUBE_URL)
    full_summary = "".join(list(summary_generator))

    assert full_summary == "Summary of Russian video."
    # Verify it tried English first, then used translation
    mock_yt_api_instance.get_transcript.assert_called_once_with(
        "test_video", languages=["en"]
    )
    mock_yt_api_instance.list_transcripts.assert_called_once_with("test_video")
    mock_translatable_transcript.translate.assert_called_once_with("en")
