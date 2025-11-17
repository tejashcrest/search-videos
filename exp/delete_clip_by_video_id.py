"""Utility script to delete all documents with a given clip_id from OpenSearch."""

import logging
import os
from typing import Optional

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv
load_dotenv()

# Constants
INDEX_NAME = "video_clips_consolidated"
CLIP_ID_TO_DELETE = "5c4e51cb-e411-43f5-bc4f-8f1f19b15eec"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_opensearch_client() -> OpenSearch:
    """Create an authenticated OpenSearch client using AWS SigV4."""
    opensearch_host = os.environ.get("OPENSEARCH_CLUSTER_HOST", "https://search-condenast-aos-domain-3hmon7me6ct3p5e46snecxe6f4.us-east-1.es.amazonaws.com")
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN')  # Optional
    if not opensearch_host:
        raise ValueError("OPENSEARCH_CLUSTER_HOST environment variable not set")

    opensearch_host = opensearch_host.replace("https://", "").replace("http://", "").strip()

    session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            aws_session_token=aws_session_token,
            region_name="us-east-1"
        )
    credentials = session.get_credentials()
    if not credentials:
        raise RuntimeError("Failed to obtain AWS credentials for OpenSearch access")

    auth = AWSV4SignerAuth(credentials, "us-east-1", "es")

    return OpenSearch(
        hosts=[{"host": opensearch_host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=5,
    )


def delete_clips_by_id(client: OpenSearch, clip_id: str) -> Optional[int]:
    """Delete all documents that match the provided clip_id."""
    delete_body = {
        "query": {
            "term": {
                "video_id": clip_id
            }
        }
    }

    logger.info("Deleting documents with clip_id=%s from index %s", clip_id, INDEX_NAME)

    response = client.delete_by_query(index=INDEX_NAME, body=delete_body, refresh=True)
    deleted = response.get("deleted", 0)
    logger.info("Delete-by-query completed. Deleted documents: %s", deleted)
    return deleted


def main() -> None:
    client = get_opensearch_client()
    deleted = delete_clips_by_id(client, CLIP_ID_TO_DELETE)
    print(f"Deleted {deleted} documents for clip_id {CLIP_ID_TO_DELETE} in index {INDEX_NAME}.")


if __name__ == "__main__":
    main()
