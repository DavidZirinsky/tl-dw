import os
import json
import requests
import re
from youtube_transcript_api import YouTubeTranscriptApi

class VideoSummarizer:
    """
    A class to summarize YouTube videos using their transcript and the OpenAI API.
    """
    def __init__(self, openai_api_key: str):
        """
        Initializes the VideoSummarizer with an OpenAI API key.

        :param openai_api_key: Your OpenAI API key.
        """
        if not openai_api_key:
            raise ValueError("OpenAI API key is required.")
        self.openai_api_key = openai_api_key

    def _extract_video_id(self, youtube_url: str) -> str:
        """Extracts the video ID from a YouTube URL."""
        video_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)', youtube_url)
        if not video_id_match:
            raise ValueError("Invalid YouTube URL provided.")
        return video_id_match.group(1)

    def _get_transcript(self, video_id: str) -> str:
        """Retrieves the transcript for a given video ID."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        except Exception as e:
            raise RuntimeError(f"Failed to get transcript: {str(e)}") from e

        transcript_content = ' '.join([entry['text'] for entry in transcript_list])
        if not transcript_content.strip():
            raise ValueError("Could not extract any text from the video (transcript is empty).")
        return transcript_content

    def summarize(self, youtube_url: str, model: str = "gpt-4o-mini"):
        """
        Summarizes a YouTube video and streams the summary.

        This is a generator function that yields chunks of the summary as they are
        received from the OpenAI API.

        :param youtube_url: The URL of the YouTube video.
        :param model: The OpenAI model to use for summarization.
        :yields: Chunks of the summary text.
        """
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
                    {"role": "system", "content": "Summarize the main points of this talk."},
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
            # A more robust implementation might log this and raise the exception.
            yield f"Error: {str(e)}"
        except Exception as e:
            yield f"An unexpected error occurred: {str(e)}"

    def summarize_and_print(self, youtube_url: str, model: str = "gpt-4o-mini"):
        """
        Calls the summarize method and prints the streaming output to the console.
        """
        print(f"Summarizing video: {youtube_url}")
        try:
            summary_chunks = self.summarize(youtube_url, model)
            
            print("\n--- Summary ---\n")
            for chunk in summary_chunks:
                print(chunk, end="", flush=True)
            print("\n\n--- End of Summary ---")

        except Exception as e:
            print(f"\nAn error occurred: {e}")


# Example usage for local development and testing
if __name__ == '__main__':
    # This is an example of how to use the VideoSummarizer class.
    # It requires the OPENAI_API_KEY environment variable to be set.
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
    else:
        # Example YouTube URL. Replace with any other video.
        # Make sure the video has English subtitles.
        video_url = "https://www.youtube.com/watch?v=LCEmiRjPEtQ" # Example: "What is an API?"
        
        summarizer = VideoSummarizer(openai_api_key=api_key)
        summarizer.summarize_and_print(video_url)
