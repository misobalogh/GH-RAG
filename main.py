import os
import logging

import dotenv
from src.ingestion.github_client import GitHubClient
from src.ingestion.repo_crawler import RepoCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    dotenv.load_dotenv()

    gh_token = os.getenv("GH_TOKEN")

    with GitHubClient(token=gh_token) as gh_client:
        logger.info(f"Authenticated as {gh_client.username}")

        crawler = RepoCrawler(client=gh_client, use_cache=True)

        files, repos = crawler.crawl_all_repos(include_private=True, max_repos=3)

        logger.info(f"Crawled {len(repos)} repositories.")
        logger.info(f"Downloaded {len(files)} files.")

        for repo in repos:
            logger.info(
                f"  - {repo.name}: {repo.total_commits} commits, "
                f"languages: {list(repo.languages.keys())}"
            )


if __name__ == "__main__":
    main()
