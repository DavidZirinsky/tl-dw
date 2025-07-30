from unittest.mock import MagicMock, patch

import pytest
import requests

from tldw import tldw

YOUTUBE_URL = "https://www.youtube.com/watch?v=test_video"


#    Tests the successful generation of a summary.
@patch("tldw.tldw.YouTubeTranscriptApi.fetch")
@patch("tldw.tldw.requests.post")
def test_successful_summary_generation(mock_requests_post, mock_fetch):

    mock_entry1 = MagicMock()
    mock_entry1.text = "Hello"
    mock_entry2 = MagicMock()
    mock_entry2.text = "world."
    mock_fetch.return_value = [mock_entry1, mock_entry2]

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
    mock_fetch.assert_called_once_with("test_video", languages=["en"])
    mock_requests_post.assert_called_once()


# Tests successful summary generation from a translated transcript.
@patch("tldw.tldw.requests.post")
@patch("tldw.tldw.YouTubeTranscriptApi.list")
@patch("tldw.tldw.YouTubeTranscriptApi.fetch")
def test_successful_summary_with_translation(mock_fetch, mock_list, mock_requests_post):
    # Mock fetch to fail to trigger translation fallback
    mock_fetch.side_effect = Exception("No direct English transcript")

    # Mock list to return a translatable transcript
    mock_translatable_transcript = MagicMock()
    mock_translatable_transcript.is_translatable = True
    mock_list.return_value = [mock_translatable_transcript]

    # Mock the translation process
    mock_translated_transcript = MagicMock()
    mock_translatable_transcript.translate.return_value = mock_translated_transcript

    # Mock the translated transcript content
    mock_entry1 = MagicMock()
    mock_entry1.text = "Translated"
    mock_entry2 = MagicMock()
    mock_entry2.text = "content."
    mock_translated_transcript.fetch.return_value = [mock_entry1, mock_entry2]

    # Mock the OpenAI API call
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_lines.return_value = [
        b'data: {"choices": [{"delta": {"content": "Translated "}}]}',
        b'data: {"choices": [{"delta": {"content": "summary."}}]}',
        b"data: [DONE]",
    ]
    mock_requests_post.return_value.__enter__.return_value = mock_response

    summarizer = tldw(openai_api_key="fake_key")
    summary_generator = summarizer.stream_summary(YOUTUBE_URL)
    full_summary = "".join(list(summary_generator))

    assert full_summary == "Translated summary."
    mock_fetch.assert_called_once_with("test_video", languages=["en"])
    mock_list.assert_called_once_with("test_video")
    mock_translatable_transcript.translate.assert_called_once_with("en")
    mock_translated_transcript.fetch.assert_called_once()
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
@patch("tldw.tldw.YouTubeTranscriptApi.fetch")
def test_transcript_fetch_failure(mock_fetch):
    mock_fetch.side_effect = Exception("Failed to fetch transcript")
    summarizer = tldw(openai_api_key="fake_key")

    result = list(summarizer.stream_summary(YOUTUBE_URL))

    assert len(result) == 1
    assert "Error: Failed to get transcript:" in result[0]


#  Tests that a ValueError is raised for an empty transcript.
@patch("tldw.tldw.YouTubeTranscriptApi.fetch")
def test_empty_transcript(mock_fetch):
    mock_entry = MagicMock()
    mock_entry.text = " "
    mock_fetch.return_value = [mock_entry]
    summarizer = tldw(openai_api_key="fake_key")

    result = list(summarizer.stream_summary(YOUTUBE_URL))

    assert len(result) == 1
    assert (
        "Error: Could not extract any text from the video (transcript is empty)."
        in result[0]
    )


# Tests that an error is yielded when the OpenAI API returns an HTTP error.
@patch("tldw.tldw.YouTubeTranscriptApi.fetch")
@patch("tldw.tldw.requests.post")
def test_openai_api_http_error(mock_requests_post, mock_fetch):
    mock_entry = MagicMock()
    mock_entry.text = "Test transcript."
    mock_fetch.return_value = [mock_entry]

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
@patch("tldw.tldw.YouTubeTranscriptApi.fetch")
@patch("tldw.tldw.requests.post")
def test_malformed_json_from_openai(mock_requests_post, mock_fetch):
    mock_entry = MagicMock()
    mock_entry.text = "Test transcript."
    mock_fetch.return_value = [mock_entry]

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
