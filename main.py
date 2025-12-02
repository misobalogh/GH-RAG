import logging
import os

import dotenv
from tree_sitter_language_pack import get_parser
from rich.logging import RichHandler
from rich import print


from src.ingestion import GitHubClient, RepoCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler()]
)
logger = logging.getLogger(__name__)


def main():
    dotenv.load_dotenv()

    gh_token = os.getenv("GH_TOKEN")

    with GitHubClient(token=gh_token) as gh_client:
        logger.info(f"Authenticated as {gh_client.username}")

        crawler = RepoCrawler(client=gh_client, use_cache=True)

        all_repos = gh_client.get_repos()
        # repo_names  = ["misobalogh/rudu", "misobalogh/utilities"]
        # repo_names  = ["misobalogh/utilities"]
        repo_names  = ["misobalogh/rudu"]
        repos = []
        files = []
        for repo in all_repos:
            if repo.full_name in repo_names:
                repo_metadata = gh_client.get_repo_metadata(repo)
                repos.append(repo_metadata)
                files.extend(crawler.crawl_repo(repo))

        # files, repos = crawler.crawl_all_repos(include_private=True, max_repos=3)

        logger.info(f"Crawled {len(repos)} repositories.")
        logger.info(f"Downloaded {len(files)} files.")

        for repo in repos:
            logger.info(
                f"  - {repo.name}: {repo.total_commits} commits, "
                f"languages: {list(repo.languages.keys())}"
            )


        rust_parser = get_parser("rust")


        def extract_python_chunks(root, source_code: str):
            chunks = []
            for child in root.children:
                if child.type in ("function_definition", "class_definition"):
                    start_byte = child.start_byte
                    end_byte = child.end_byte
                    chunk_text = source_code[start_byte:end_byte]
                    chunks.append((child.type, chunk_text))
            return chunks


        def extract_rust_chunks(root, source_code: str):
            chunks = []
            for child in root.children:
                if child.type in ("use_declaration", "line_comment"):
                    start_byte = child.start_byte
                    end_byte = child.end_byte
                    chunk_text = source_code[start_byte:end_byte]
                    chunks.append((child.type, chunk_text))
            return chunks


        for file in files:
            if file.language == "Rust":
                tree = rust_parser.parse(file.content.encode("utf8"))
                root = tree.root_node
                logger.info(f"Parsed AST for {file.path} in {file.repo_name}")
                logger.info(f"  - Root node type: {root.type}, children: {root.children}")

                chunks = extract_rust_chunks(root, file.content)
                for chunk_type, chunk_text in chunks:
                    logger.info(f"Chunk type: {chunk_type}\n{chunk_text}\n")

            if file.language == "Python":
                tree = rust_parser.parse(file.content.encode("utf8"))
                root = tree.root_node
                logger.info(f"Parsed AST for {file.path} in {file.repo_name}")
                logger.info(f"  - Root node type: {root.type}, children: {root.children}")

                chunks = extract_python_chunks(root, file.content)
                for chunk_type, chunk_text in chunks:
                    logger.info(f"Chunk type: {chunk_type}\n{chunk_text}\n")

if __name__ == "__main__":
    main()
