import json
import logging
import os
import re
from typing import Generator, Optional

import pyfiglet
import requests
from termcolor import colored
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

logger = logging.getLogger(__name__)


# A class to summarize YouTube videos using their transcript and the OpenAI API.
class VideoSummarizer:
    def __init__(self, openai_api_key: str, proxies: Optional[dict] = None):
        if not openai_api_key:
            raise ValueError("OpenAI API key is required.")
        self.openai_api_key = openai_api_key
        proxy_config = None
        if proxies:
            proxy_config = GenericProxyConfig(
                http_url=proxies.get("http"), https_url=proxies.get("https")
            )
        self.ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)

    # Extracts the video ID from a YouTube URL
    def _extract_video_id(self, youtube_url: str) -> str:
        video_id_match = re.search(
            r"(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)", youtube_url
        )
        if not video_id_match:
            raise ValueError("Invalid YouTube URL provided.")
        return video_id_match.group(1)

    # Retrieves the transcript for a given video ID
    def _get_transcript(self, video_id: str) -> str:
        try:
            # First, try to fetch the English transcript directly using fetch().
            # This returns a FetchedTranscript object which is iterable over snippets.
            transcript = self.ytt_api.fetch(video_id, languages=["en"])
            transcript_content = " ".join([entry.text for entry in transcript])
        except Exception:
            # If English is not available, find a translatable transcript.
            try:
                transcript_list = self.ytt_api.list(video_id)
                translatable_transcript = next(
                    t for t in transcript_list if t.is_translatable
                )
                translated_transcript = translatable_transcript.translate("en")
                # .fetch() on a translated transcript returns a list of snippet objects.
                # The error "not subscriptable" means we must use attribute access (.text).
                fetched_snippets = translated_transcript.fetch()
                transcript_content = " ".join(
                    [entry.text for entry in fetched_snippets]
                )
            except StopIteration:
                raise RuntimeError(
                    f"No translatable transcript found for video {video_id}."
                ) from None
            except Exception as e:
                raise RuntimeError(f"Failed to get transcript: {str(e)}") from e

        if not transcript_content.strip():
            raise ValueError(
                "Could not extract any text from the video (transcript is empty)."
            )
        return transcript_content

    # Summarizes a YouTube video and streams the summary.
    def stream_summary(
        self, youtube_url: str, model: str = "gpt-4o-mini"
    ) -> Generator[str, None, None]:
        try:
            video_id = self._extract_video_id(youtube_url)
            transcript = self._get_transcript(video_id)

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Summarize the main points of this talk.",
                    },
                    {"role": "user", "content": transcript},
                ],
                "stream": True,
            }

            with requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
            ) as llm_response:
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
                                yield content
                        except (json.JSONDecodeError, KeyError):
                            # Ignore malformed chunks or chunks without content
                            continue

        except (requests.exceptions.RequestException, ValueError, RuntimeError) as e:
            # Yield a single error message if something goes wrong.
            yield f"Error: {str(e)}"
        except Exception as e:
            yield f"An unexpected error occurred: {str(e)}"

    #  Calls the summarize method and prints the streaming output to the console.
    def summarize(self, youtube_url: str, model: str = "gpt-4o-mini") -> None:
        ascii_art = pyfiglet.figlet_format("TLDW", font="slant")
        print(ascii_art)  # noqa
        print(f"Summarizing video: {youtube_url}")  # noqa
        try:
            summary_chunks = self.stream_summary(youtube_url, model)

            print(colored("\n--- Summary ---\n", "green"))  # noqa
            for chunk in summary_chunks:
                print(chunk, end="", flush=True)  # noqa
            print(colored("\n\n--- End of Summary ---", "green"))  # noqa

        except Exception as e:
            logger.error(f"\nAn error occurred: {e}")


# Example usage for local development and testing
if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("Error: OPENAI_API_KEY environment variable not set.")
    else:
        # Example YouTube URL. Replace with any other video.
        video_url = "https://www.youtube.com/watch?v=MtkgT6R2HtA"

        summarizer = VideoSummarizer(openai_api_key=api_key)
        summarizer.summarize(video_url)
