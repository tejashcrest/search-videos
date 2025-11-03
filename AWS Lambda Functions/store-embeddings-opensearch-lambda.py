# import json
# import boto3
# import os
# import subprocess
# import tempfile
# from opensearchpy import OpenSearch, RequestsHttpConnection
# from requests_aws4auth import AWS4Auth
# import uuid


# def lambda_handler(event, context):
#     """
#     Read embeddings from S3, generate thumbnails for unique clips, and index into OpenSearch Serverless
#     """
#     try:
#         # Extract parameters from Step Functions
#         output_s3_path = event['outputS3Path']
#         part = event['part']
#         original_video = event['originalVideo']
        
#         # Use video key as ID (more meaningful than UUID)
#         video_id = str(uuid.uuid4())
        
#         print(f"Processing embeddings for part {part}")
#         print(f"Video ID: {video_id}")
#         print(f"Output S3 path: {output_s3_path}")
        
#         # Initialize clients
#         s3_client = boto3.client('s3', region_name='us-east-1')
#         opensearch_client = get_opensearch_client()
        
#         # Parse S3 path
#         bucket, key = parse_s3_uri(output_s3_path)
        
#         # Download embeddings from S3
#         embeddings_data = download_embeddings_from_s3(s3_client, bucket, key)
        
#         if not embeddings_data:
#             raise ValueError("No embeddings data found in S3")

#         print(f"✓ Successfully downloaded embeddings for part {part}")
        
#         # Generate thumbnails for unique clips using streaming
#         thumbnails = generate_thumbnails_streaming(
#             s3_client,
#             original_video['bucket'],
#             original_video['key'],
#             embeddings_data,
#             bucket,
#             key  # Store in thumbnails/ folder under same prefix
#         )
        
#         print(f"✓ Generated {len(thumbnails)} unique thumbnails")
        
#         # Index embeddings to OpenSearch with validation
#         indexed_count = index_embeddings_to_opensearch(
#             opensearch_client,
#             embeddings_data,
#             thumbnails,
#             video_id,
#             original_video,
#             part
#         )
        
#         print(f"✓ Successfully indexed {indexed_count} embeddings for part {part}")
        
#         return {
#             'statusCode': 200,
#             'part': part,
#             'videoId': video_id,
#             'embeddingsIndexed': indexed_count,
#             'thumbnailsGenerated': len(thumbnails),
#             'message': 'Successfully stored embeddings in OpenSearch'
#         }
        
#     except Exception as e:
#         print(f"Error storing embeddings: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         raise


# def get_opensearch_client():
#     """Initialize OpenSearch Serverless client with AWS authentication"""
#     opensearch_host = os.environ['OPENSEARCH_SERVERLESS_HOST']
#     opensearch_host = opensearch_host.replace('https://', '').replace('http://', '').strip()
    
#     session = boto3.Session()
#     credentials = session.get_credentials()
    
#     awsauth = AWS4Auth(
#         credentials.access_key,
#         credentials.secret_key,
#         'us-east-1',
#         'aoss',
#         session_token=credentials.token
#     )
    
#     client = OpenSearch(
#         hosts=[{'host': opensearch_host, 'port': 443}],
#         http_auth=awsauth,
#         use_ssl=True,
#         verify_certs=True,
#         connection_class=RequestsHttpConnection,
#         pool_maxsize=20
#     )
    
#     # Ensure index exists
#     create_index_if_not_exists(client)
    
#     return client


# def create_index_if_not_exists(client):
#     """Create video_clips index if it doesn't exist"""
#     index_name = "video_clips"
    
#     if not client.indices.exists(index=index_name):
#         index_body = {
#             "settings": {
#                 "index": {
#                     "knn": True
#                 }
#             },
#             "mappings": {
#                 "properties": {
#                     "video_id": {"type": "keyword"},
#                     "video_path": {"type": "keyword"},
#                     "part": {"type": "integer"},
#                     "segment_index": {"type": "integer"},
#                     "timestamp_start": {"type": "float"},
#                     "timestamp_end": {"type": "float"},
#                     "clip_text": {"type": "text"},
#                     "embedding_scope": {"type": "keyword"},
#                     "thumbnail_url": {"type": "keyword"},
#                     "embedding": {
#                         "type": "knn_vector",
#                         "dimension": 1024,
#                         "method": {
#                             "name": "hnsw",
#                             "space_type": "l2",
#                             "engine": "faiss",
#                             "parameters": {
#                                 "ef_construction": 128,
#                                 "m": 16
#                             }
#                         }
#                     }
#                 }
#             }
#         }
        
#         client.indices.create(index=index_name, body=index_body)
#         print(f"Created index: {index_name}")


# def parse_s3_uri(s3_uri: str) -> tuple:
#     """Parse S3 URI into bucket and key"""
#     s3_parts = s3_uri.replace('s3://', '').split('/', 1)
#     bucket = s3_parts[0]
#     key = s3_parts[1] if len(s3_parts) > 1 else ''
#     return bucket, key


# def download_embeddings_from_s3(s3_client, bucket: str, key_prefix: str) -> dict:
#     """Download embeddings from S3, handling Bedrock's output structure"""
#     possible_keys = [
#         f"{key_prefix}/output.json"
#     ]
    
#     for key in possible_keys:
#         try:
#             print(f"Trying to read from s3://{bucket}/{key}")
#             obj = s3_client.get_object(Bucket=bucket, Key=key)
#             result = json.loads(obj['Body'].read().decode('utf-8'))
#             print(f"Successfully read embeddings from S3")
#             return result
#         except s3_client.exceptions.NoSuchKey:
#             continue
#         except Exception as e:
#             print(f"Error reading from S3 key {key}: {e}")
#             continue
    
#     raise ValueError(f"Could not find embeddings output in S3 at {bucket}/{key_prefix}")


# def generate_presigned_url(s3_client, bucket: str, key: str, expiration: int = 3600) -> str:
#     """Generate presigned URL for S3 object"""
#     try:
#         url = s3_client.generate_presigned_url(
#             'get_object',
#             Params={'Bucket': bucket, 'Key': key},
#             ExpiresIn=expiration
#         )
#         return url
#     except Exception as e:
#         print(f"Error generating presigned URL: {e}")
#         raise


# def generate_thumbnails_streaming(s3_client, video_bucket, video_key, 
#                                  embeddings_data, thumbnail_bucket, embeddings_prefix):
#     """
#     Generate thumbnails using streaming from S3 (no video download required)
#     Uses presigned URL + ffmpeg HTTP streaming
    
#     Returns: dict mapping (start_time, end_time) -> thumbnail S3 URI
#     """
#     thumbnails = {}
#     unique_clips = {}
    
#     if 'data' not in embeddings_data:
#         return thumbnails
    
#     segments = embeddings_data['data']
    
#     # Step 1: Find unique clips based on timestamp
#     for idx, segment in enumerate(segments):
#         start_time = round(segment.get('startSec', 0), 2)
#         end_time = round(segment.get('endSec', 0), 2)
#         clip_key = (start_time, end_time)
        
#         # Store only first occurrence of each unique clip
#         if clip_key not in unique_clips:
#             unique_clips[clip_key] = {
#                 'index': idx,
#                 'start': start_time,
#                 'end': end_time,
#                 'scope': segment.get('embeddingOption', 'clip')
#             }
    
#     print(f"Found {len(unique_clips)} unique clips from {len(segments)} segments")
    
#     # Step 2: Generate presigned URL for video
#     try:
#         # Generate presigned URL valid for 1 hour
#         video_url = generate_presigned_url(s3_client, video_bucket, video_key, 3600)
#         print(f"Generated presigned URL for video streaming")
        
#         # Calculate thumbnail S3 prefix
#         if 'embeddings/' in embeddings_prefix:
#             thumbnail_prefix = embeddings_prefix.replace('embeddings/', 'thumbnails/')
#         else:
#             thumbnail_prefix = embeddings_prefix.replace('/output.json', '/thumbnails')
        
#         # Step 3: Generate thumbnails using streaming
#         with tempfile.TemporaryDirectory() as tmpdir:
#             generated_count = 0
            
#             for clip_key, clip_info in unique_clips.items():
#                 try:
#                     start_time = clip_info['start']
#                     end_time = clip_info['end']
                    
#                     # Generate thumbnail filename
#                     thumbnail_filename = f"clip_{int(start_time*100)}_{int(end_time*100)}.jpg"
#                     thumbnail_path = f"{tmpdir}/{thumbnail_filename}"
                    
#                     # Use ffmpeg to extract frame directly from streaming URL
#                     cmd = [
#                         'ffmpeg',
#                         '-ss', str(start_time),          # Seek to timestamp
#                         '-i', video_url,                 # Input: presigned S3 URL
#                         '-vframes', '1',                 # Extract 1 frame
#                         '-q:v', '2',                     # High quality
#                         '-vf', 'scale=320:180',          # Resize to thumbnail (optional)
#                         '-y',                            # Overwrite output
#                         thumbnail_path
#                     ]
                    
#                     result = subprocess.run(
#                         cmd,
#                         check=True,
#                         capture_output=True,
#                         timeout=30,  # Increased timeout for streaming
#                         text=True
#                     )
                    
#                     # Upload thumbnail to S3
#                     thumbnail_s3_key = f"{thumbnail_prefix}/{thumbnail_filename}"
#                     s3_client.upload_file(
#                         thumbnail_path,
#                         thumbnail_bucket,
#                         thumbnail_s3_key,
#                         ExtraArgs={'ContentType': 'image/jpeg'}
#                     )
                    
#                     thumbnail_uri = f"s3://{thumbnail_bucket}/{thumbnail_s3_key}"
#                     thumbnails[clip_key] = thumbnail_uri
                    
#                     generated_count += 1
#                     if generated_count % 5 == 0:
#                         print(f"Generated {generated_count}/{len(unique_clips)} thumbnails")
                    
#                 except subprocess.TimeoutExpired:
#                     print(f"⚠️ Timeout generating thumbnail for clip {clip_key}")
#                     thumbnails[clip_key] = None
#                 except subprocess.CalledProcessError as e:
#                     print(f"⚠️ FFmpeg error for clip {clip_key}: {e.stderr}")
#                     thumbnails[clip_key] = None
#                 except Exception as e:
#                     print(f"⚠️ Error generating thumbnail for clip {clip_key}: {e}")
#                     thumbnails[clip_key] = None
#                     continue
            
#             print(f"✓ Successfully generated {generated_count} thumbnails via streaming")
    
#     except Exception as e:
#         print(f"Error in streaming thumbnail generation: {e}")
#         import traceback
#         traceback.print_exc()
    
#     return thumbnails


# def validate_embedding(embedding, expected_dim=1024):
#     """Validate embedding dimensions and data"""
#     if not isinstance(embedding, list):
#         return False, f"Embedding is not a list: {type(embedding)}"
    
#     if len(embedding) != expected_dim:
#         return False, f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}"
    
#     # Check if all elements are numbers
#     for i, val in enumerate(embedding):
#         if not isinstance(val, (int, float)):
#             return False, f"Embedding contains non-numeric value at index {i}: {val}"
#         if val != val:  # Check for NaN
#             return False, f"Embedding contains NaN at index {i}"
    
#     return True, "Valid"


# def index_embeddings_to_opensearch(opensearch_client, embeddings_data: dict,
#                                    thumbnails: dict, video_id: str, 
#                                    original_video: dict, part: int) -> int:
#     """Index embeddings into OpenSearch with validation (includes thumbnails)"""
#     index_name = "video_clips"
#     indexed_count = 0
    
#     # Parse embeddings from Bedrock response format
#     if 'data' in embeddings_data:
#         segments = embeddings_data['data']
#     else:
#         segments = []
    
#     print(f"Found {len(segments)} segments to index")
    
#     for idx, segment in enumerate(segments):
#         try:
#             # Extract embedding
#             embedding = segment.get('embedding', [])
            
#             # Validate embedding BEFORE indexing
#             is_valid, validation_msg = validate_embedding(embedding)
            
#             if not is_valid:
#                 print(f"⚠️ Skipping segment {idx}: {validation_msg}")
#                 print(f"   First 5 values: {embedding[:5] if len(embedding) >= 5 else embedding}")
#                 continue
            
#             # Get clip timestamp key for thumbnail lookup
#             start_time = round(segment.get('startSec', 0), 2)
#             end_time = round(segment.get('endSec', 0), 2)
#             clip_key = (start_time, end_time)
            
#             # Prepare document
#             doc = {
#                 'video_id': video_id,
#                 'video_path': f"s3://{original_video['bucket']}/{original_video['key']}",
#                 'part': part,
#                 'segment_index': idx,
#                 'timestamp_start': float(segment.get('startSec', 0)),
#                 'timestamp_end': float(segment.get('endSec', 0)),
#                 'clip_text': original_video['key'].split('/')[-1],
#                 'embedding_scope': segment.get('embeddingOption', 'clip'),
#                 'embedding': embedding,
#                 'thumbnail_url': thumbnails.get(clip_key)  # Same thumbnail for audio/visual-image/visual-text
#             }
            
#             # Index document
#             response = opensearch_client.index(
#                 index=index_name,
#                 body=doc
#             )
            
#             indexed_count += 1
            
#             if indexed_count % 10 == 0:
#                 print(f"Indexed {indexed_count}/{len(segments)} segments")
            
#         except Exception as e:
#             print(f"Error indexing segment {idx}: {e}")
#             print(f"  Embedding length: {len(embedding) if 'embedding' in locals() else 'N/A'}")
#             print(f"  Segment keys: {segment.keys()}")
#             continue
    
#     return indexed_count

#################### Serverless Collection w/o thumbnails
# import json
# import boto3
# import os
# import hashlib
# from opensearchpy import OpenSearch, RequestsHttpConnection
# from requests_aws4auth import AWS4Auth
# import uuid


# def lambda_handler(event, context):
#     """
#     Read embeddings from S3 and index into OpenSearch Serverless
#     """
#     try:
#         # Extract parameters from Step Functions
#         output_s3_path = event['outputS3Path']
#         part = event['part']
#         original_video = event['originalVideo']
        
#         # Use video key as ID (more meaningful than UUID)
#         video_id = str(uuid.uuid4())
        
#         print(f"Processing embeddings for part {part}")
#         print(f"Video ID: {video_id}")
#         print(f"Output S3 path: {output_s3_path}")
        
#         # Initialize clients
#         s3_client = boto3.client('s3', region_name='us-east-1')
#         opensearch_client = get_opensearch_client()
        
#         # Parse S3 path
#         bucket, key = parse_s3_uri(output_s3_path)
        
#         # Download embeddings from S3
#         embeddings_data = download_embeddings_from_s3(s3_client, bucket, key)
        
#         if not embeddings_data:
#             raise ValueError("No embeddings data found in S3")

#         print(f"✓ Successfully downloaded embeddings for part {part}")
        
#         # Index embeddings to OpenSearch with validation
#         indexed_count = index_embeddings_to_opensearch(
#             opensearch_client,
#             embeddings_data,
#             video_id,
#             original_video,
#             part
#         )
        
#         print(f"✓ Successfully indexed {indexed_count} embeddings for part {part}")
        
#         return {
#             'statusCode': 200,
#             'part': part,
#             'videoId': video_id,
#             'embeddingsIndexed': indexed_count,
#             'message': 'Successfully stored embeddings in OpenSearch'
#         }
        
#     except Exception as e:
#         print(f"Error storing embeddings: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         raise


# def get_opensearch_client():
#     """Initialize OpenSearch Serverless client with AWS authentication"""
#     opensearch_host = os.environ['OPENSEARCH_SERVERLESS_HOST']
#     opensearch_host = opensearch_host.replace('https://', '').replace('http://', '').strip()
    
#     session = boto3.Session()
#     credentials = session.get_credentials()
    
#     awsauth = AWS4Auth(
#         credentials.access_key,
#         credentials.secret_key,
#         'us-east-1',
#         'aoss',
#         session_token=credentials.token
#     )
    
#     client = OpenSearch(
#         hosts=[{'host': opensearch_host, 'port': 443}],
#         http_auth=awsauth,
#         use_ssl=True,
#         verify_certs=True,
#         connection_class=RequestsHttpConnection,
#         pool_maxsize=20
#     )
    
#     # Ensure index exists
#     create_index_if_not_exists(client)
    
#     return client


# def create_index_if_not_exists(client):
#     """Create video_clips index if it doesn't exist"""
#     index_name = "video_clips"
    
#     if not client.indices.exists(index=index_name):
#         index_body = {
#             "settings": {
#                 "index": {
#                     "knn": True
#                 }
#             },
#             "mappings": {
#                 "properties": {
#                     "video_id": {"type": "keyword"},
#                     "video_path": {"type": "keyword"},
#                     "clip_id": {"type": "keyword"},  # Unique ID for each clip (same for all modalities)
#                     "part": {"type": "integer"},
#                     "segment_index": {"type": "integer"},
#                     "timestamp_start": {"type": "float"},
#                     "timestamp_end": {"type": "float"},
#                     "clip_text": {"type": "text"},
#                     "embedding_scope": {"type": "keyword"},
#                     "embedding": {
#                         "type": "knn_vector",
#                         "dimension": 1024,
#                         "method": {
#                             "name": "hnsw",
#                             "space_type": "l2",
#                             "engine": "faiss",
#                             "parameters": {
#                                 "ef_construction": 128,
#                                 "m": 16
#                             }
#                         }
#                     }
#                 }
#             }
#         }
        
#         client.indices.create(index=index_name, body=index_body)
#         print(f"Created index: {index_name}")


# def generate_clip_id(video_id: str, start_time: float, end_time: float) -> str:
#     """
#     Generate deterministic clip_id based on video_id and timestamps
#     Same clip (different modalities) will have the same clip_id
    
#     Args:
#         video_id: Video identifier
#         start_time: Clip start timestamp
#         end_time: Clip end timestamp
    
#     Returns:
#         Deterministic clip_id (hash of video_id + timestamps)
#     """
#     # Create a deterministic string from video_id and timestamps
#     clip_string = f"{video_id}_{start_time:.2f}_{end_time:.2f}"
    
#     # Generate SHA256 hash and take first 16 characters for shorter ID
#     clip_hash = hashlib.sha256(clip_string.encode()).hexdigest()[:16]
    
#     return f"clip_{clip_hash}"


# def parse_s3_uri(s3_uri: str) -> tuple:
#     """Parse S3 URI into bucket and key"""
#     s3_parts = s3_uri.replace('s3://', '').split('/', 1)
#     bucket = s3_parts[0]
#     key = s3_parts[1] if len(s3_parts) > 1 else ''
#     return bucket, key


# def download_embeddings_from_s3(s3_client, bucket: str, key_prefix: str) -> dict:
#     """Download embeddings from S3, handling Bedrock's output structure"""
#     possible_keys = [
#         f"{key_prefix}/output.json"
#     ]
    
#     for key in possible_keys:
#         try:
#             print(f"Trying to read from s3://{bucket}/{key}")
#             obj = s3_client.get_object(Bucket=bucket, Key=key)
#             result = json.loads(obj['Body'].read().decode('utf-8'))
#             print(f"Successfully read embeddings from S3")
#             return result
#         except s3_client.exceptions.NoSuchKey:
#             continue
#         except Exception as e:
#             print(f"Error reading from S3 key {key}: {e}")
#             continue
    
#     raise ValueError(f"Could not find embeddings output in S3 at {bucket}/{key_prefix}")


# def validate_embedding(embedding, expected_dim=1024):
#     """Validate embedding dimensions and data"""
#     if not isinstance(embedding, list):
#         return False, f"Embedding is not a list: {type(embedding)}"
    
#     if len(embedding) != expected_dim:
#         return False, f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}"
    
#     # Check if all elements are numbers
#     for i, val in enumerate(embedding):
#         if not isinstance(val, (int, float)):
#             return False, f"Embedding contains non-numeric value at index {i}: {val}"
#         if val != val:  # Check for NaN
#             return False, f"Embedding contains NaN at index {i}"
    
#     return True, "Valid"


# def index_embeddings_to_opensearch(opensearch_client, embeddings_data: dict,
#                                    video_id: str, original_video: dict, part: int) -> int:
#     """Index embeddings into OpenSearch with validation (includes clip_id for collapse)"""
#     index_name = "video_clips"
#     indexed_count = 0
    
#     # Parse embeddings from Bedrock response format
#     if 'data' in embeddings_data:
#         segments = embeddings_data['data']
#     else:
#         segments = []
    
#     print(f"Found {len(segments)} segments to index")
    
#     for idx, segment in enumerate(segments):
#         try:
#             # Extract embedding
#             embedding = segment.get('embedding', [])
            
#             # Validate embedding BEFORE indexing
#             is_valid, validation_msg = validate_embedding(embedding)
            
#             if not is_valid:
#                 print(f"⚠️ Skipping segment {idx}: {validation_msg}")
#                 print(f"   First 5 values: {embedding[:5] if len(embedding) >= 5 else embedding}")
#                 continue
            
#             # Get clip timestamps
#             start_time = round(segment.get('startSec', 0), 2)
#             end_time = round(segment.get('endSec', 0), 2)
            
#             # Generate deterministic clip_id (same for all modalities of this clip)
#             clip_id = generate_clip_id(video_id, start_time, end_time)
            
#             # Prepare document with clip_id
#             doc = {
#                 'video_id': video_id,
#                 'video_path': f"s3://{original_video['bucket']}/{original_video['key']}",
#                 'clip_id': clip_id,  # Same for audio/visual-image/visual-text
#                 'part': part,
#                 'segment_index': idx,
#                 'timestamp_start': float(segment.get('startSec', 0)),
#                 'timestamp_end': float(segment.get('endSec', 0)),
#                 'clip_text': original_video['key'].split('/')[-1],
#                 'embedding_scope': segment.get('embeddingOption', 'clip'),
#                 'embedding': embedding
#             }
            
#             # Index document
#             response = opensearch_client.index(
#                 index=index_name,
#                 body=doc
#             )
            
#             indexed_count += 1
            
#             if indexed_count % 10 == 0:
#                 print(f"Indexed {indexed_count}/{len(segments)} segments")
            
#         except Exception as e:
#             print(f"Error indexing segment {idx}: {e}")
#             print(f"  Embedding length: {len(embedding) if 'embedding' in locals() else 'N/A'}")
#             print(f"  Segment keys: {segment.keys()}")
#             continue
    
#     return indexed_count

############################ Cluster w/o thumbnails
import json
import boto3
import os
import hashlib
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from typing import Dict
import uuid


def lambda_handler(event, context):
    """
    Read embeddings from S3 and index into OpenSearch Cluster
    """
    try:
        # Extract parameters from Step Functions
        output_s3_path = event['outputS3Path']
        part = event['part']
        original_video = event['originalVideo']
        
        # Use video key as ID
        video_id = str(uuid.uuid4())
        
        print(f"Processing embeddings for part {part}")
        print(f"Video ID: {video_id}")
        print(f"Output S3 path: {output_s3_path}")
        
        # Initialize clients
        s3_client = boto3.client('s3', region_name='us-east-1')
        opensearch_client = get_opensearch_client()
        
        # Parse S3 path
        bucket, key = parse_s3_uri(output_s3_path)
        
        # Download embeddings from S3
        embeddings_data = download_embeddings_from_s3(s3_client, bucket, key)
        
        if not embeddings_data:
            raise ValueError("No embeddings data found in S3")

        print(f"✓ Successfully downloaded embeddings for part {part}")
        
        # Index embeddings to OpenSearch with validation
        indexed_count = index_embeddings_to_opensearch(
            opensearch_client,
            embeddings_data,
            video_id,
            original_video,
            part
        )
        
        print(f"✓ Successfully indexed {indexed_count} embeddings for part {part}")
        
        return {
            'statusCode': 200,
            'part': part,
            'videoId': video_id,
            'embeddingsIndexed': indexed_count,
            'message': 'Successfully stored embeddings in OpenSearch'
        }
        
    except Exception as e:
        print(f"Error storing embeddings: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def get_opensearch_client():
    """Initialize OpenSearch Cluster client with AWS authentication"""
    # CHANGE 1: Use cluster endpoint instead of serverless
    opensearch_host = os.environ['OPENSEARCH_CLUSTER_HOST']  # e.g., search-xxx.us-east-1.es.amazonaws.com
    opensearch_host = opensearch_host.replace('https://', '').replace('http://', '').strip()
    
    # CHANGE 2: Use AWSV4SignerAuth instead of AWS4Auth
    session = boto3.Session()
    credentials = session.get_credentials()
    
    auth = AWSV4SignerAuth(credentials, 'us-east-1', 'es')  # 'es' instead of 'aoss'
    
    # CHANGE 3: Port 443 and connection settings remain same, but auth changes
    client = OpenSearch(
        hosts=[{'host': opensearch_host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20
    )
    
    # Ensure index exists
    create_index_if_not_exists(client)
    
    return client


def create_index_if_not_exists(client):
    """Create video_clips index if it doesn't exist"""
    index_name = "video_clips"
    
    if not client.indices.exists(index=index_name):
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    # CHANGE 4: Add cluster-specific settings (optional)
                    "number_of_shards": 2,
                    "number_of_replicas": 1
                }
            },
            "mappings": {
                "properties": {
                    "video_id": {"type": "keyword"},
                    "video_path": {"type": "keyword"},
                    "clip_id": {"type": "keyword"},
                    "part": {"type": "integer"},
                    "segment_index": {"type": "integer"},
                    "timestamp_start": {"type": "float"},
                    "timestamp_end": {"type": "float"},
                    "clip_text": {"type": "text"},
                    "embedding_scope": {"type": "keyword"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            # CHANGE 5: Use 'lucene' or 'nmslib' for cluster (faiss also supported)
                            "engine": "lucene",  # or "nmslib" or "faiss"
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16
                            }
                        }
                    }
                }
            }
        }
        
        client.indices.create(index=index_name, body=index_body)
        print(f"Created index: {index_name}")


def generate_clip_id(video_id: str, start_time: float, end_time: float) -> str:
    """Generate deterministic clip_id based on video_id and timestamps"""
    clip_string = f"{video_id}_{start_time:.2f}_{end_time:.2f}"
    clip_hash = hashlib.sha256(clip_string.encode()).hexdigest()[:16]
    return f"clip_{clip_hash}"


def parse_s3_uri(s3_uri: str) -> tuple:
    """Parse S3 URI into bucket and key"""
    s3_parts = s3_uri.replace('s3://', '').split('/', 1)
    bucket = s3_parts[0]
    key = s3_parts[1] if len(s3_parts) > 1 else ''
    return bucket, key


def download_embeddings_from_s3(s3_client, bucket: str, key_prefix: str) -> dict:
    """Download embeddings from S3, handling Bedrock's output structure"""
    possible_keys = [
        f"{key_prefix}/output.json"
    ]
    
    for key in possible_keys:
        try:
            print(f"Trying to read from s3://{bucket}/{key}")
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            result = json.loads(obj['Body'].read().decode('utf-8'))
            print(f"Successfully read embeddings from S3")
            return result
        except s3_client.exceptions.NoSuchKey:
            continue
        except Exception as e:
            print(f"Error reading from S3 key {key}: {e}")
            continue
    
    raise ValueError(f"Could not find embeddings output in S3 at {bucket}/{key_prefix}")


def validate_embedding(embedding, expected_dim=1024):
    """Validate embedding dimensions and data"""
    if not isinstance(embedding, list):
        return False, f"Embedding is not a list: {type(embedding)}"
    
    if len(embedding) != expected_dim:
        return False, f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}"
    
    for i, val in enumerate(embedding):
        if not isinstance(val, (int, float)):
            return False, f"Embedding contains non-numeric value at index {i}: {val}"
        if val != val:  # Check for NaN
            return False, f"Embedding contains NaN at index {i}"
    
    return True, "Valid"


def index_embeddings_to_opensearch(opensearch_client, embeddings_data: dict,
                                   video_id: str, original_video: dict, part: int) -> int:
    """Index embeddings into OpenSearch with validation"""
    index_name = "video_clips"
    indexed_count = 0
    
    if 'data' in embeddings_data:
        segments = embeddings_data['data']
    else:
        segments = []
    
    print(f"Found {len(segments)} segments to index")
    
    for idx, segment in enumerate(segments):
        try:
            embedding = segment.get('embedding', [])
            
            is_valid, validation_msg = validate_embedding(embedding)
            
            if not is_valid:
                print(f"⚠️ Skipping segment {idx}: {validation_msg}")
                print(f"   First 5 values: {embedding[:5] if len(embedding) >= 5 else embedding}")
                continue
            
            start_time = round(segment.get('startSec', 0), 2)
            end_time = round(segment.get('endSec', 0), 2)
            
            clip_id = generate_clip_id(video_id, start_time, end_time)
            
            doc = {
                'video_id': video_id,
                'video_path': f"s3://{original_video['bucket']}/{original_video['key']}",
                'clip_id': clip_id,
                'part': part,
                'segment_index': idx,
                'timestamp_start': float(segment.get('startSec', 0)),
                'timestamp_end': float(segment.get('endSec', 0)),
                'clip_text': original_video['key'].split('/')[-1],
                'embedding_scope': segment.get('embeddingOption', 'clip'),
                'embedding': embedding
            }
            
            response = opensearch_client.index(
                index=index_name,
                body=doc
            )
            
            indexed_count += 1
            
            if indexed_count % 10 == 0:
                print(f"Indexed {indexed_count}/{len(segments)} segments")
            
        except Exception as e:
            print(f"Error indexing segment {idx}: {e}")
            print(f"  Embedding length: {len(embedding) if 'embedding' in locals() else 'N/A'}")
            print(f"  Segment keys: {segment.keys()}")
            continue
    
    return indexed_count
