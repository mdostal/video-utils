"""Judge provider interface (documentation module — no executable code).

A provider module (bin/lib/providers/<name>.py) must expose:

    def review(video_path: str, transcript: str | None, prompt: str) -> str

        video_path: absolute path to the local video file to judge.
        transcript: plain-text transcript content if available, else None.
        prompt:     the fully-resolved review prompt text (already accounts
                    for VIDEO_REVIEW_PROMPT overrides — providers never read
                    that env var themselves).

        Returns the raw judge response text: a prose "REVIEW" section plus a
        single fenced ```json block containing the clip-suggestion array.
        review.py parses this response; providers do not write any files.

Provider-specific configuration (API keys, model names, endpoints) is read
from env INSIDE the provider module itself — review.py passes only the three
review-domain inputs above and never reaches into provider internals.

Selection: VIDEO_JUDGE_PROVIDER (env, default "gemini") names the module to
import from this package. See gemini.py for the real implementation and
mock.py for a network-free provider used in tests and local iteration.
"""
