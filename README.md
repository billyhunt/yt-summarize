# yt-summarize

A CLI that fetches YouTube video transcripts, summarizes them with Claude, and saves the result to Obsidian.

## Requirements

- Python 3
- [Anthropic API key](https://console.anthropic.com/)
- [Obsidian](https://obsidian.md/) with the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin (optional)

### Install dependencies

```bash
pip3 install anthropic youtube-transcript-api
```

## Setup

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export OBSIDIAN_REST_API_KEY="your-obsidian-rest-api-key"
```

The Obsidian REST API key is found in **Obsidian → Settings → Local REST API**.

### Optional environment variables

| Variable | Default | Description |
|---|---|---|
| `OBSIDIAN_REST_PORT` | `27124` | Obsidian Local REST API port |
| `OBSIDIAN_SUMMARY_FOLDER` | `transcripts/videos` | Vault folder for saved summaries |

## Usage

```bash
python3 yt-summarize.py <youtube-url-or-video-id>
```

The summary is printed to stdout and saved to Obsidian as a markdown note with YAML frontmatter linking back to the video.

To skip saving to Obsidian:

```bash
python3 yt-summarize.py --no-obsidian <url>
```

## Example

```
$ python3 yt-summarize.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
Fetching transcript for video: dQw4w9WgXcQ ...
Video title: Rick Astley - Never Gonna Give You Up
Transcript fetched (1842 chars). Summarizing ...
...
Saved to Obsidian: transcripts/videos/Rick Astley - Never Gonna Give You Up.md
```
