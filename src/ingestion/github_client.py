import os
from pathlib import Path
from github import Auth, Github, Repository, ContentFile
from .models import RepoMetadata


class GitHubClient:
    GH_TOKEN_ENV_VAR = "GH_TOKEN"

    IGNORED_DIRS = {
        ".git",
        ".idea",
        ".vscode",
        "__pycache__",
    }

    IGNORED_FILES = {
        ".gitignore",
        ".gitattributes",
        "package-lock.json",
        "uv.lock",
        "Cargo.lock",
    }

    CODE_EXTENSIONS = {
        "py",
        # "ipynb", TODO: handle notebooks separately - add a converter
        "rs",
        "c",
        "h",
        "cpp",
        "hpp",
        "cxx",
        "cc",
        "js",
        "ts",
        "cs",
        "php",
        "r",
        "R",
        "vue",
        "html",
        "css",
        "sh",
    }

    DOC_EXTENSIONS = {
        "md",
        "txt",
        "yaml",
        "yml",
        "json",
        "toml",
        "conf",
        "cfg",
    }

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv(self.GH_TOKEN_ENV_VAR)
        if not self.token:
            raise ValueError("GitHub token is required")

        auth = Auth.Token(self.token)
        self.client = Github(auth=auth)
        self.user = self.client.get_user()

    @property
    def username(self) -> str:
        return self.user.login

    def get_repos(self, include_private: bool = True) -> list[Repository.Repository]:
        return [repo for repo in self.user.get_repos() if include_private or not repo.private]

    def get_repo_metadata(self, repo: Repository.Repository) -> RepoMetadata:
        return RepoMetadata(
            name=repo.name,
            full_name=repo.full_name,
            url=repo.html_url,
            private=repo.private,
            description=repo.description,
            languages=repo.get_languages(),
            topics=repo.get_topics(),
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            total_commits=repo.get_commits().totalCount,
        )

    def should_process_file(self, path: Path) -> bool:
        parts = set(path.parts)
        if parts.intersection(self.IGNORED_DIRS):
            return False

        if path.name in self.IGNORED_FILES:
            return False

        file_extension = path.suffix.lstrip(".")
        return file_extension in self.CODE_EXTENSIONS or file_extension in self.DOC_EXTENSIONS

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
