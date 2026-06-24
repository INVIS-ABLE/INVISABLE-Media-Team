"""Local, file-based store for the 5090 Studio Engine.

No database, no server, no network — every post is a plain JSON file under a local
export root, organised into folders that mirror its lifecycle::

    <export_dir>/generated      freshly generated, awaiting review
    <export_dir>/approved       approved locally
    <export_dir>/rejected       rejected locally
    <export_dir>/ready_to_post  exported & packaged for posting by hand

Approving / rejecting moves the JSON between folders; exporting writes a clean,
paste-ready ``.md`` next to the JSON in ``ready_to_post`` so the founder can post
it from any machine with nothing but a file browser.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from invisable_os.config import get_settings
from invisable_os.models.studio import StudioPost, StudioStatus

# The folder names are exactly the status values, so a post always lives in the
# folder that matches its status.
_FOLDERS = (
    StudioStatus.GENERATED,
    StudioStatus.APPROVED,
    StudioStatus.REJECTED,
    StudioStatus.READY_TO_POST,
)


class StudioStore:
    """Persists :class:`StudioPost` objects to local folders. Fully offline."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        root = Path(base_dir) if base_dir is not None else Path(get_settings().export_dir)
        self.root = root
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for folder in _FOLDERS:
            (self.root / folder.value).mkdir(parents=True, exist_ok=True)

    # -- paths ---------------------------------------------------------------

    def _dir(self, status: StudioStatus) -> Path:
        return self.root / status.value

    def _path(self, post: StudioPost) -> Path:
        return self._dir(post.status) / f"{post.id}.json"

    def _find_path(self, post_id: str) -> Path | None:
        for folder in _FOLDERS:
            candidate = self._dir(folder) / f"{post_id}.json"
            if candidate.exists():
                return candidate
        return None

    # -- write ---------------------------------------------------------------

    def save_batch(self, posts: list[StudioPost]) -> list[StudioPost]:
        """Write a freshly generated batch to ``generated/``. Stamps ``created_at``."""
        now = datetime.now(UTC).isoformat(timespec="seconds")
        for post in posts:
            if not post.created_at:
                post.created_at = now
            post.status = StudioStatus.GENERATED
            self._write(post)
        return posts

    def _write(self, post: StudioPost) -> StudioPost:
        path = self._path(post)
        path.write_text(post.model_dump_json(indent=2), encoding="utf-8")
        return post

    # -- read ----------------------------------------------------------------

    def get(self, post_id: str) -> StudioPost | None:
        path = self._find_path(post_id)
        if path is None:
            return None
        return StudioPost.model_validate_json(path.read_text(encoding="utf-8"))

    def list_posts(self, status: StudioStatus | str | None = None) -> list[StudioPost]:
        """Return posts, optionally filtered to a single status, newest first."""
        folders = (
            [StudioStatus(status)] if status is not None else list(_FOLDERS)
        )
        posts: list[StudioPost] = []
        for folder in folders:
            for path in self._dir(folder).glob("*.json"):
                try:
                    posts.append(StudioPost.model_validate_json(path.read_text(encoding="utf-8")))
                except Exception:  # noqa: BLE001 — skip a corrupt file, never crash review
                    continue
        posts.sort(key=lambda p: p.created_at, reverse=True)
        return posts

    # -- transitions ---------------------------------------------------------

    def _move(self, post_id: str, to: StudioStatus) -> StudioPost | None:
        old = self._find_path(post_id)
        if old is None:
            return None
        post = StudioPost.model_validate_json(old.read_text(encoding="utf-8"))
        post.status = to
        self._write(post)
        new = self._path(post)
        if old.resolve() != new.resolve():
            old.unlink(missing_ok=True)
        return post

    def approve(self, post_id: str) -> StudioPost | None:
        return self._move(post_id, StudioStatus.APPROVED)

    def reject(self, post_id: str) -> StudioPost | None:
        return self._move(post_id, StudioStatus.REJECTED)

    def edit(self, post_id: str, fields: dict) -> StudioPost | None:
        """Apply local edits to a post's editorial fields in place."""
        path = self._find_path(post_id)
        if path is None:
            return None
        post = StudioPost.model_validate_json(path.read_text(encoding="utf-8"))
        editable = {
            "hook", "caption", "hashtags", "script", "visual_idea",
            "founder_presence_suggestion", "platform", "format", "notes",
        }
        data = post.model_dump()
        for key, value in fields.items():
            if key in editable:
                data[key] = value
        edited = StudioPost.model_validate(data)
        self._write(edited)
        return edited

    # -- export --------------------------------------------------------------

    def export_approved(self) -> dict:
        """Move every approved post to ``ready_to_post`` and write a paste-ready file.

        Returns a small summary: how many were exported and the folder they're in.
        """
        exported: list[str] = []
        for post in self.list_posts(StudioStatus.APPROVED):
            moved = self._move(post.id, StudioStatus.READY_TO_POST)
            if moved is None:
                continue
            self._write_markdown(moved)
            exported.append(moved.id)
        return {
            "exported": len(exported),
            "ids": exported,
            "folder": str(self._dir(StudioStatus.READY_TO_POST)),
        }

    def _write_markdown(self, post: StudioPost) -> Path:
        """A clean, human-readable post package next to the JSON."""
        md = self._dir(StudioStatus.READY_TO_POST) / f"{post.id}.md"
        tags = " ".join(post.hashtags)
        body = (
            f"# {post.platform.value} · {post.format.value} · {post.pillar}\n\n"
            f"**Hook:** {post.hook}\n\n"
            f"## Caption\n\n{post.caption}\n\n"
            f"{tags}\n\n"
            f"## Script\n\n{post.script}\n\n"
            f"## Visual idea\n\n{post.visual_idea}\n\n"
            f"## Founder presence\n\n{post.founder_presence_suggestion}\n\n"
            f"---\n"
            f"risk={post.risk_score} · mission={post.mission_score} · "
            f"humour={post.humour_score} · authenticity={post.authenticity_score}\n"
        )
        md.write_text(body, encoding="utf-8")
        return md

    # -- stats ---------------------------------------------------------------

    def stats(self) -> dict:
        return {folder.value: len(list(self._dir(folder).glob("*.json"))) for folder in _FOLDERS}


_singleton: StudioStore | None = None


def get_studio_store() -> StudioStore:
    """Return a process-wide Studio store rooted at the configured export dir."""
    global _singleton
    if _singleton is None:
        _singleton = StudioStore()
    return _singleton


def reset_studio_store() -> None:
    """Drop the cached store (tests point the export dir at a temp folder)."""
    global _singleton
    _singleton = None
