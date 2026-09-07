"""Network-free judge provider for tests and local iteration.

No API key, no network call. Returns a fixed REVIEW section plus a fixed
1-item clips.json array. If a transcript is passed, it's echoed back into the
response so callers can assert transcript pass-through without a real API.
Select with VIDEO_JUDGE_PROVIDER=mock.
"""


def review(video_path, transcript, prompt):
    transcript_line = f"\n\n(mock saw transcript: {transcript.strip()})" if transcript else ""
    return f"""## REVIEW
Mock review for {video_path}. This is a canned response from the mock
provider (VIDEO_JUDGE_PROVIDER=mock) — no network call was made.{transcript_line}

## CLIPS_JSON
```json
[{{"start": "0:00", "end": "0:01", "label": "mock-clip", "why": "canned mock response"}}]
```
"""
