####### Previous version contained just replicating the data exactly in same index, now updating it to have new and different index in which data would be replicated


from dotenv import load_dotenv
import os
import json
import time
import logging
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, helpers
import boto3
from typing import Tuple
import random

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_opensearch_client():
    opensearch_host = os.getenv('OPENSEARCH_CLUSTER_HOST')
    if not opensearch_host:
        raise ValueError("OPENSEARCH_CLUSTER_HOST not set")
    opensearch_host = opensearch_host.replace('https://', '').replace('http://', '').strip()
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN')
    region = os.getenv('AWS_REGION', 'us-east-1')
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token,
        region_name=region
    )
    credentials = session.get_credentials()
    auth = AWSV4SignerAuth(credentials, region, 'es')
    client = OpenSearch(
        hosts=[{'host': opensearch_host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
        timeout=120,
        connection_timeout=30
    )
    client.info()
    return client

SOURCE_INDEX = "video_clips_3"
TARGET_INDEX = "video_clips_3_lucene"
EMBEDDING_DIMENSIONS = 512

client = get_opensearch_client()

# Define target index with new structure and lucene engine
def get_target_index_definition():
    """
    Define the target index with optimized settings for Marengo 3.0 embeddings.
    Uses lucene engine for better hybrid/RRF performance.
    """
    return {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 512,
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "refresh_interval": "5s"
            }
        },
        "mappings": {
            "properties": {                
                # 1. Visual Vector (Marengo 3.0 = 512 dims)
                "emb_visual": {
                    "type": "knn_vector",
                    "dimension": EMBEDDING_DIMENSIONS,
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        "space_type": "cosinesimil",
                        "parameters": {
                            "m": 24,
                            "ef_construction": 512
                        }
                    }
                },
                
                # 2. Audio Vector (Marengo 3.0 = 512 dims)
                "emb_audio": {
                    "type": "knn_vector",
                    "dimension": EMBEDDING_DIMENSIONS,
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        "space_type": "cosinesimil",
                        "parameters": {
                            "m": 24,
                            "ef_construction": 512
                        }
                    }
                },
                
                # 3. Transcription Vector (Marengo 3.0 = 512 dims)
                "emb_transcription": {
                    "type": "knn_vector",
                    "dimension": EMBEDDING_DIMENSIONS,
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        "space_type": "cosinesimil",
                        "parameters": {
                            "m": 32,
                            "ef_construction": 512
                        }
                    }
                }
            }
        }
    }

def ensure_target_index_exists(client: OpenSearch, target_index: str) -> bool:
    """Create target index with new definition if it doesn't exist."""
    if client.indices.exists(index=target_index):
        logger.info(f"Target index '{target_index}' already exists")
        return True
    
    index_body = get_target_index_definition()
    client.indices.create(index=target_index, body=index_body)
    logger.info(f"✓ Created target index '{target_index}' with new structure")
    return True




def is_valid_embedding(embedding) -> bool:
    """
    Validate if an embedding vector is not empty and has valid values.
    
    Args:
        embedding: List of floats representing the embedding vector
        
    Returns:
        bool: True if embedding is valid (non-empty and not all zeros), False otherwise
    """
    if not embedding or not isinstance(embedding, list):
        return False
    if len(embedding) == 0:
        return False
    # Check if all values are zero (invalid embedding)
    if all(v == 0 for v in embedding):
        return False
    return True

def validate_embeddings(source_doc: dict) -> Tuple[bool, dict]:
    """
    Validate embedding columns in source document.
    
    Args:
        source_doc: Source document from OpenSearch
        
    Returns:
        Tuple of (is_valid, validation_info) where is_valid indicates if document should be copied
    """
    embedding_fields = ['emb_visual', 'emb_audio', 'emb_transcription']
    validation_info = {
        'item_id': source_doc.get('_id', 'unknown'),
        'video_id': source_doc.get('_source', {}).get('video_id', 'unknown'),
        'valid_embeddings': [],
        'missing_embeddings': [],
        'is_valid': False
    }
    
    source = source_doc.get('_source', {})
    
    for field in embedding_fields:
        embedding = source.get(field)
        if is_valid_embedding(embedding):
            validation_info['valid_embeddings'].append(field)
        else:
            validation_info['missing_embeddings'].append(field)
    
    # Document is valid if it has at least one valid embedding
    validation_info['is_valid'] = len(validation_info['valid_embeddings']) > 0
    
    return validation_info['is_valid'], validation_info

def bulk_copy(client: OpenSearch, source_index: str, target_index: str, batch_size: int = 500) -> dict:
    """
    Copy documents from source to target index with embedding validation.
    Only copies documents that have at least one valid embedding vector.
    Tracks item IDs and validation status.
    Handles rate limiting with exponential backoff.
    """
    total = 0
    created = 0
    errors = 0
    skipped = 0
    skipped_items = []
    start = time.time()
    
    scan_iter = helpers.scan(
        client,
        index=source_index,
        query={ 'query': { 'match_all': {} } },
        size=batch_size,
        scroll='2m'
    )

    def gen_actions():
        nonlocal skipped, skipped_items
        for hit in scan_iter:
            # Validate embeddings
            is_valid, validation_info = validate_embeddings(hit)
            
            if not is_valid:
                skipped += 1
                skipped_items.append(validation_info)
                logger.warning(
                    f"⊘ Skipping item {validation_info['item_id']} "
                    f"(video_id: {validation_info['video_id']}) - "
                    f"No valid embeddings found"
                )
                continue
            
            # Log valid embeddings
            logger.debug(
                f"✓ Processing item {validation_info['item_id']} "
                f"(video_id: {validation_info['video_id']}) - "
                f"Valid embeddings: {', '.join(validation_info['valid_embeddings'])}"
            )
            
            yield {
                '_op_type': 'create',
                '_index': target_index,
                '_id': hit.get('_id'),
                '_source': hit.get('_source', {})
            }

    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            for ok, info in helpers.streaming_bulk(
                client,
                gen_actions(),
                chunk_size=100,
                request_timeout=60,
                raise_on_error=False,
                max_retries=3,
                initial_backoff=2,
            ):
                total += 1
                if ok:
                    created += 1
                else:
                    errors += 1
                    if 'error' in info:
                        logger.error(f"✗ Error creating document: {info.get('error', 'Unknown error')}")
            
            # Success - break out of retry loop
            break
            
        except Exception as e:
            if '429' in str(e) or 'Too Many Requests' in str(e):
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = (2 ** retry_count) + random.uniform(0, 1)
                    logger.warning(f"Rate limited (429). Retry {retry_count}/{max_retries} after {wait_time:.1f}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max retries ({max_retries}) exceeded. Giving up.")
                    raise
            else:
                logger.error(f"Bulk copy error: {e}", exc_info=True)
                raise

    return {
        'took_sec': round(time.time() - start, 2),
        'total_attempted': total,
        'created': created,
        'errors': errors,
        'skipped': skipped,
        'skipped_items_sample': skipped_items[:10]  # Show first 10 skipped items
    }

if __name__ == "__main__":
    start = time.time()
    
    logger.info("=" * 80)
    logger.info("Starting data replication with embedding validation")
    logger.info(f"Source Index: {SOURCE_INDEX}")
    logger.info(f"Target Index: {TARGET_INDEX}")
    logger.info(f"Embedding Dimensions: {EMBEDDING_DIMENSIONS}")
    logger.info("=" * 80)
    
    # Create target index with new definition
    logger.info("Step 1: Creating target index with new structure...")
    ensure_target_index_exists(client, TARGET_INDEX)
    
    # Bulk copy with validation and rate limit handling
    logger.info("Step 2: Starting bulk copy with embedding validation...")
    res = bulk_copy(client, SOURCE_INDEX, TARGET_INDEX)
    method = 'bulk_with_validation'
    
    # Get final counts
    logger.info("Step 3: Verifying replication...")
    src_cnt = int(client.cat.count(index=SOURCE_INDEX, format='json')[0]['count'])
    dst_cnt = int(client.cat.count(index=TARGET_INDEX, format='json')[0]['count'])
    
    summary = {
        'status': 'completed',
        'method': method,
        'source_index': SOURCE_INDEX,
        'target_index': TARGET_INDEX,
        'source_count': src_cnt,
        'target_count': dst_cnt,
        'took_sec': round(time.time() - start, 2),
        'details': res
    }
    
    logger.info("=" * 80)
    logger.info("Replication Summary:")
    logger.info(json.dumps(summary, indent=2))
    logger.info("=" * 80)
    
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(json.dumps(summary, indent=2))
    print("=" * 80)