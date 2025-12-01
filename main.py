import os
from pprint import pprint

import dotenv
from src.ingestion.github_client import GitHubClient

def main():
    dotenv.load_dotenv()

    gh_token = os.getenv("GH_TOKEN")

    with GitHubClient(token=gh_token) as gh_client:
        repos = gh_client.get_repos(include_private=False)
        for repo in repos:
            print(f"Repository: {repo.full_name}, Private: {repo.private}")
            metadata = gh_client.get_repo_metadata(repo)
            pprint(metadata)
            print()



if __name__ == "__main__":
    main()
