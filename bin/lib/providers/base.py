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

A provider MAY additionally expose a second, OPTIONAL capability:

    def pick_frame(image_paths: list[str], prompt: str) -> int

        image_paths: local paths to candidate thumbnail frame images (JPEG).
        prompt:      the fully-resolved instruction text for picking one.

        Returns a 1-based index into image_paths naming the chosen frame,
        clamped/defaulted to 1 by the provider if its own response can't be
        parsed (never raises for that reason). review() and pick_frame() are
        independent capabilities — a provider may implement either, both, or
        neither; callers (e.g. bin/thumbnail.py) MUST check
        `hasattr(provider, "pick_frame")` before calling it and must treat
        any exception it raises (including a fatal key-lookup SystemExit) as
        a soft failure — picking is always a best-effort enhancement, never
        a requirement for the caller's other work to have succeeded.
"""
