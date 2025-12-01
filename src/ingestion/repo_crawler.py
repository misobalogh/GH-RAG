import base64
import logging
from contextlib import suppress
from pathlib import Path

from github import ContentFile, GithubException, Repository

from src.ingestion.cache import RepoCache
from src.ingestion.github_client import GitHubClient
from src.ingestion.models import FileContent, RepoMetadata

logger = logging.getLogger(__name__)


class RepoCrawler:
    MAX_FILE_SIZE_MB = 1 * 1024 * 1024  # 1 MB

    def __init__(self, client: GitHubClient, use_cache: bool = True):
        self.client = client
        self._processed_repos: list[RepoMetadata] = []
        self._files: list[FileContent] = []
        self.use_cache = use_cache
        self._cache = RepoCache() if use_cache else None

    def crawl_repo(self, repo: Repository.Repository) -> list[FileContent]:
        if self._cache:
            cached = self._cache.load(repo)
            if cached:
                files, metadata = cached
                self._processed_repos.append(metadata)
                self._files.extend(files)
                return files

        files: list[FileContent] = []
        metadata = self.client.get_repo_metadata(repo)
        self._processed_repos.append(metadata)

        logger.info(f"Crawling repository: {repo.full_name}")

        try:
            initial_contents = repo.get_contents("")
        except Exception as e:
            logger.warning(
                f"Cannot access contents of repository {repo.full_name}: {e}"
            )
            return files

        contents: list[ContentFile.ContentFile] = (
            initial_contents
            if isinstance(initial_contents, list)
            else [initial_contents]
        )

        while contents:
            file_content = contents.pop(0)

            if file_content.type == "dir":
                if file_content.name in self.client.IGNORED_DIRS:
                    continue

                try:
                    dir_contents = repo.get_contents(file_content.path)
                    if isinstance(dir_contents, list):
                        # Multiple items, extend contents
                        contents.extend(dir_contents)
                    else:
                        # Single item, add it back to contents
                        contents.append(dir_contents)
                except GithubException:
                    continue

            else:
                if not self.client.should_process_file(Path(file_content.path)):
                    continue

                if file_content.size > self.MAX_FILE_SIZE_MB:
                    logger.debug(f"Skipping large file: {file_content.path}")
                    continue

                try:
                    file_data = self._extract_file_content(
                        content_file=file_content, repo=repo
                    )
                    if file_data:
                        files.append(file_data)
                        logger.debug(f"Processed: {file_content.path}")
                except Exception as e:
                    logger.warning(f"Error processing {file_content.path}: {e}")

        self._files.extend(files)
        logger.info(f"Crawled {len(files)} files from {repo.full_name}")

        if self._cache:
            self._cache.save(repo.full_name, files, metadata)

        return files

    def _extract_file_content(
        self,
        content_file,
        repo: Repository.Repository,
    ) -> FileContent | None:
        try:
            if content_file.encoding == "base64":
                decoded = base64.b64decode(content_file.content).decode("utf-8")
            else:
                decoded = content_file.content or ""
        except (UnicodeDecodeError, TypeError):
            # Binary file or decoding error, skip
            return None

        if not decoded.strip():
            # Empty file after stripping, skip
            return None

        last_modified = self._get_last_modified_date(repo, content_file.path)

        return FileContent(
            path=content_file.path,
            content=decoded,
            language=self.client.get_language(content_file.path),
            repo_name=repo.full_name,
            repo_url=repo.html_url,
            last_modified=last_modified,
            size=content_file.size,
        )

    def _get_last_modified_date(self, repo: Repository.Repository, file_path: str):
        with suppress(GithubException):
            commits = repo.get_commits(path=file_path)
            if commits.totalCount:
                return commits[0].commit.author.date
        return None

    def crawl_all_repos(
        self, include_private: bool = True, max_repos: int | None = None
    ) -> tuple[list[FileContent], list[RepoMetadata]]:
        repos = self.client.get_repos(include_private=include_private)

        if max_repos:
            repos = repos[:max_repos]

        all_files = []
        for repo in repos:
            files = self.crawl_repo(repo)
            all_files.extend(files)

        return all_files, self._processed_repos

    @property
    def processed_repos(self) -> list[RepoMetadata]:
        return self._processed_repos

    @property
    def all_files(self) -> list[FileContent]:
        return self._files
