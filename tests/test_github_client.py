import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.ingestion.github_client import GitHubClient


class TestGitHubClientInit:
    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def test_init_with_token_param(self, mock_auth, mock_github):
        mock_user = MagicMock()
        mock_github.return_value.get_user.return_value = mock_user

        client = GitHubClient(token="test-token")

        mock_auth.Token.assert_called_once_with("test-token")
        assert client.token == "test-token"

    @patch.dict("os.environ", {"GH_TOKEN": "env-token"})
    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def test_init_with_env_token(self, mock_auth, mock_github):
        mock_github.return_value.get_user.return_value = MagicMock()

        client = GitHubClient()

        mock_auth.Token.assert_called_once_with("env-token")
        assert client.token == "env-token"

    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_token_raises(self):
        with pytest.raises(ValueError, match="GitHub token is required"):
            GitHubClient()


class TestGitHubClientProperties:
    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def test_username(self, mock_auth, mock_github):
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.return_value.get_user.return_value = mock_user

        client = GitHubClient(token="test-token")

        assert client.username == "testuser"


class TestGetRepos:
    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def test_get_repos_include_private(self, mock_auth, mock_github):
        mock_user = MagicMock()
        private_repo = MagicMock(private=True)
        public_repo = MagicMock(private=False)
        mock_user.get_repos.return_value = [private_repo, public_repo]
        mock_github.return_value.get_user.return_value = mock_user

        client = GitHubClient(token="test-token")
        repos = client.get_repos(include_private=True)

        assert len(repos) == 2
        assert private_repo in repos
        assert public_repo in repos

    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def test_get_repos_exclude_private(self, mock_auth, mock_github):
        mock_user = MagicMock()
        private_repo = MagicMock(private=True)
        public_repo = MagicMock(private=False)
        mock_user.get_repos.return_value = [private_repo, public_repo]
        mock_github.return_value.get_user.return_value = mock_user

        client = GitHubClient(token="test-token")
        repos = client.get_repos(include_private=False)

        assert len(repos) == 1
        assert public_repo in repos
        assert private_repo not in repos


class TestShouldProcessFile:
    @pytest.fixture
    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def client(self, mock_auth, mock_github):
        mock_github.return_value.get_user.return_value = MagicMock()
        return GitHubClient(token="test-token")

    @pytest.mark.parametrize("ignored_dir", [".git", ".idea", ".vscode", "__pycache__"])
    def test_ignored_directories(self, client, ignored_dir):
        path = Path(f"{ignored_dir}/somefile.py")
        assert client.should_process_file(path) is False

    @pytest.mark.parametrize("ignored_file", [".gitignore", ".gitattributes", "package-lock.json", "uv.lock", "Cargo.lock"])
    def test_ignored_files(self, client, ignored_file):
        path = Path(f"src/{ignored_file}")
        assert client.should_process_file(path) is False

    @pytest.mark.parametrize("ext", ["py", "rs", "js", "ts", "cpp", "c", "h", "cs", "php", "vue", "html", "css", "sh"])
    def test_code_extensions_allowed(self, client, ext):
        path = Path(f"src/main.{ext}")
        assert client.should_process_file(path) is True

    @pytest.mark.parametrize("ext", ["md", "txt", "yaml", "yml", "json", "toml", "conf", "cfg"])
    def test_doc_extensions_allowed(self, client, ext):
        path = Path(f"docs/readme.{ext}")
        assert client.should_process_file(path) is True

    def test_unknown_extension_rejected(self, client):
        path = Path("src/image.png")
        assert client.should_process_file(path) is False

    def test_nested_ignored_dir(self, client):
        path = Path("src/__pycache__/module.cpython-311.pyc")
        assert client.should_process_file(path) is False


class TestContextManager:
    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def test_context_manager(self, mock_auth, mock_github):
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        mock_client.get_user.return_value = MagicMock()

        with GitHubClient(token="test-token") as client:
            assert client is not None

        mock_client.close.assert_called_once()

    @patch("src.ingestion.github_client.Github")
    @patch("src.ingestion.github_client.Auth")
    def test_close(self, mock_auth, mock_github):
        mock_client = MagicMock()
        mock_github.return_value = mock_client
        mock_client.get_user.return_value = MagicMock()

        client = GitHubClient(token="test-token")
        client.close()

        mock_client.close.assert_called_once()
