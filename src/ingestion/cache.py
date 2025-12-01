import json
import logging
from datetime import datetime
from pathlib import Path

from github import Repository

from src.ingestion.models import FileContent, RepoMetadata

logger = logging.getLogger(__name__)


class RepoCache:
    DEFAULT_CACHE_DIR = Path(".cache/repos")

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, repo_full_name: str) -> Path:
        safe_name = repo_full_name.replace("/", "_")
        return self.cache_dir / f"{safe_name}.json"

    def load(
        self, repo: Repository.Repository
    ) -> tuple[list[FileContent], RepoMetadata] | None:
        cache_path = self._get_cache_path(repo.full_name)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)

            cached_updated = (
                datetime.fromisoformat(data["metadata"]["updated_at"])
                if data["metadata"]["updated_at"]
                else None
            )

            # Check if repo was updated since cache
            if cached_updated and repo.updated_at and repo.updated_at > cached_updated:
                logger.info(f"Cache outdated for {repo.full_name}, re-crawling")
                return None

            metadata = RepoMetadata(
                name=data["metadata"]["name"],
                full_name=data["metadata"]["full_name"],
                url=data["metadata"]["url"],
                private=data["metadata"]["private"],
                description=data["metadata"]["description"],
                languages=data["metadata"]["languages"],
                topics=data["metadata"]["topics"],
                created_at=datetime.fromisoformat(data["metadata"]["created_at"])
                if data["metadata"]["created_at"]
                else None,
                updated_at=cached_updated,
                total_commits=data["metadata"]["total_commits"],
            )

            files = [
                FileContent(
                    path=f["path"],
                    content=f["content"],
                    language=f["language"],
                    repo_name=f["repo_name"],
                    repo_url=f["repo_url"],
                    last_modified=datetime.fromisoformat(f["last_modified"])
                    if f["last_modified"]
                    else None,
                    size=f["size"],
                )
                for f in data["files"]
            ]

            logger.info(f"Loaded {len(files)} files from cache for {repo.full_name}")
            return files, metadata

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid cache for {repo.full_name}: {e}")
            return None

    def save(
        self, repo_full_name: str, files: list[FileContent], metadata: RepoMetadata
    ):
        cache_path = self._get_cache_path(repo_full_name)
        data = {
            "metadata": {
                "name": metadata.name,
                "full_name": metadata.full_name,
                "url": metadata.url,
                "private": metadata.private,
                "description": metadata.description,
                "languages": metadata.languages,
                "topics": metadata.topics,
                "created_at": metadata.created_at.isoformat()
                if metadata.created_at
                else None,
                "updated_at": metadata.updated_at.isoformat()
                if metadata.updated_at
                else None,
                "total_commits": metadata.total_commits,
            },
            "files": [
                {
                    "path": f.path,
                    "content": f.content,
                    "language": f.language,
                    "repo_name": f.repo_name,
                    "repo_url": f.repo_url,
                    "last_modified": f.last_modified.isoformat()
                    if f.last_modified
                    else None,
                    "size": f.size,
                }
                for f in files
            ],
        }
        with open(cache_path, "w") as f:
            json.dump(data, f)
        logger.debug(f"Saved {len(files)} files to cache for {repo_full_name}")

    def clear(self, repo_full_name: str | None = None):
        if repo_full_name:
            cache_path = self._get_cache_path(repo_full_name)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache for {repo_full_name}")
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared all cache")
