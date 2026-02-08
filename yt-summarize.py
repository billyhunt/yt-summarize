#!/usr/bin/env python3
"""YouTube Video Summarizer CLI - Fetches a transcript and summarizes it using Claude."""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.request

import anthropic
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """Extract the video ID from various YouTube URL formats."""
    patterns = [
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/watch\?.*v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/v/)([a-zA-Z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    # Maybe the argument is already a bare video ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url):
        return url
    print(f"Error: Could not extract video ID from: {url}", file=sys.stderr)
    sys.exit(1)


def fetch_video_title(video_id: str) -> str:
    """Fetch the video title from YouTube's oembed endpoint."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
            return data["title"]
    except Exception:
        return video_id  # Fall back to video ID as the title


def fetch_transcript(video_id: str) -> str:
    """Fetch the transcript for a YouTube video, preferring manual English captions."""
    try:
        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list(video_id)

        # Try manual English transcripts first
        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
        except Exception:
            # Fall back to auto-generated English
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
            except Exception:
                # Last resort: grab whatever is available and translate
                transcript = next(iter(transcript_list))
                transcript = transcript.translate("en")

        entries = transcript.fetch()
        return " ".join(snippet.text for snippet in entries)
    except Exception as e:
        print(f"Error fetching transcript: {e}", file=sys.stderr)
        sys.exit(1)


def summarize(transcript: str) -> str:
    """Send the transcript to Claude and return a structured summary."""
    client = anthropic.Anthropic()

    # Truncate very long transcripts to stay within reasonable token limits
    max_chars = 100_000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[transcript truncated]"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Below is a transcript of a YouTube video. "
                    "Please provide a structured summary with:\n"
                    "1. A one-line TLDR\n"
                    "2. Key points (bulleted)\n"
                    "3. A brief conclusion\n\n"
                    "Keep the summary concise and readable.\n\n"
                    f"TRANSCRIPT:\n{transcript}"
                ),
            }
        ],
    )
    return message.content[0].text


def send_to_obsidian(title: str, video_id: str, summary: str) -> None:
    """Send the summary to Obsidian via the Local REST API plugin."""
    api_key = os.environ.get("OBSIDIAN_REST_API_KEY")
    if not api_key:
        print("Error: OBSIDIAN_REST_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    port = int(os.environ.get("OBSIDIAN_REST_PORT", "27124"))
    folder = os.environ.get("OBSIDIAN_SUMMARY_FOLDER", "transcripts/videos")

    # Sanitize title for use as a filename
    safe_title = re.sub(r'[\\/:*?"<>|]', "-", title).strip()
    note_path = f"{folder}/{safe_title}.md"

    note_content = (
        f"---\n"
        f"source: https://www.youtube.com/watch?v={video_id}\n"
        f"type: youtube-summary\n"
        f"---\n\n"
        f"{summary}\n"
    )

    url = f"https://127.0.0.1:{port}/vault/{urllib.request.quote(note_path, safe='/')}"

    # Trust the plugin's self-signed certificate
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        data=note_content.encode("utf-8"),
        method="PUT",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "text/markdown",
        },
    )

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            if resp.status < 300:
                print(f"Saved to Obsidian: {note_path}", file=sys.stderr)
    except Exception as e:
        print(f"Error sending to Obsidian: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Summarize a YouTube video using its transcript and Claude.")
    parser.add_argument("url", help="YouTube video URL or video ID")
    parser.add_argument("--no-obsidian", action="store_true", help="Skip sending the summary to Obsidian")
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    print(f"Fetching transcript for video: {video_id} ...", file=sys.stderr)

    title = fetch_video_title(video_id)
    print(f"Video title: {title}", file=sys.stderr)

    transcript = fetch_transcript(video_id)
    print(f"Transcript fetched ({len(transcript)} chars). Summarizing ...", file=sys.stderr)

    summary = summarize(transcript)
    print(summary)

    if not args.no_obsidian:
        send_to_obsidian(title, video_id, summary)


if __name__ == "__main__":
    main()
