from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RepoMetadata:
    name: str
    full_name: str
    url: str
    private: bool
    description: str | None = None
    languages: dict[str, int] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    total_commits: int = 0


@dataclass
class FileContent:
    path: str
    content: str
    language: str | None
    repo_name: str
    repo_url: str
    last_modified: datetime | None = None
    size: int = 0
