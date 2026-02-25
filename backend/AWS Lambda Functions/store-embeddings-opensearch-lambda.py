import json
import boto3
import os
import hashlib
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from typing import Dict, List, Optional
import uuid
from collections import defaultdict
from datetime import datetime
import subprocess
import tempfile
import shutil

# Configuration from environment variables
THUMBNAIL_BUCKET = os.environ.get('THUMBNAIL_BUCKET')
THUMBNAIL_PREFIX = 'thumbnails/'
EMBEDDING_DIMENSIONS = 512
INDEX_NAME = 'video_clips_3_lucene'
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

def lambda_handler(event, context):
    """
    Read embeddings from S3 and index into OpenSearch Cluster
    Consolidates all modalities per clip into single documents with thumbnails
    """
    try:
        # Extract parameters from Step Functions
        output_s3_path = event['outputS3Path']
        part = event['part']
        original_video = event['originalVideo']
        categories = event.get('categories', ['Uncategorized'])
        
        # Use video key as ID
        video_id = str(uuid.uuid4())
        
        print(f"Processing embeddings for part {part}")
        print(f"Video ID: {video_id}")
        print(f"Output S3 path: {output_s3_path}")
        print(f"Region: {AWS_REGION}")
        print(f"Thumbnail bucket: {THUMBNAIL_BUCKET}")
        
        # Initialize clients with dynamic region
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        opensearch_client = get_opensearch_client()
        
        # Parse S3 path
        bucket, key = parse_s3_uri(output_s3_path)
        
        # Download embeddings from S3
        embeddings_data = download_embeddings_from_s3(s3_client, bucket, key)
        
        if not embeddings_data:
            raise ValueError("No embeddings data found in S3")

        print(f"✓ Successfully downloaded embeddings for part {part}")
        
        # Index embeddings to OpenSearch with consolidation and thumbnails
        indexed_count = index_embeddings_to_opensearch_consolidated(
            opensearch_client,
            s3_client,
            embeddings_data,
            video_id,
            original_video,
            part,
            categories
        )
        
        print(f"✓ Successfully indexed {indexed_count} consolidated clips for part {part}")
        
        return {
            'statusCode': 200,
            'part': part,
            'videoId': video_id,
            'clipsIndexed': indexed_count,
            'message': 'Successfully stored consolidated embeddings in OpenSearch'
        }
        
    except Exception as e:
        print(f"Error storing embeddings: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def get_opensearch_client():
    """Initialize OpenSearch Cluster client with AWS authentication"""
    opensearch_host = os.environ['OPENSEARCH_CLUSTER_HOST']
    opensearch_host = opensearch_host.replace('https://', '').replace('http://', '').strip()
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Use dynamic region from environment
    auth = AWSV4SignerAuth(credentials, AWS_REGION, 'es')
    
    client = OpenSearch(
        hosts=[{'host': opensearch_host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
        timeout=30,
        retry_on_timeout=True,
        max_retries=3
    )
    
    # Ensure index exists (only on first call)
    create_index_if_not_exists(client)
    
    return client


def create_index_if_not_exists(client):
    """
    Create production-grade consolidated video_clips index
    Optimized for accuracy, storage efficiency, and multimodal search
    """
    index_name = INDEX_NAME
    
    try:
        if client.indices.exists(index=index_name):
            print(f"✓ Index {index_name} already exists")
            return
        
        index_body = {
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
                    # Metadata fields
                    "video_id": {"type": "keyword"},
                    "video_path": {"type": "keyword"},
                    "video_name": {"type": "text"},
                    "video_duration_sec": {"type": "float"},
                    "clip_id": {"type": "keyword"},
                    "part": {"type": "integer"},
                    "timestamp_start": {"type": "float"},
                    "timestamp_end": {"type": "float"},
                    "clip_duration": {"type": "float"},
                    "clip_text": {"type": "text"},
                    "thumbnail_path": {"type": "keyword"},
                    "created_at": {"type": "date"},

                    "categories": {
                        "type": "keyword"
                    },

                    # Marengo embedding fields
                    "emb_visual": {
                        "type": "knn_vector",
                        "dimension": EMBEDDING_DIMENSIONS,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 32
                            }
                        }
                    },
                    "emb_transcription": {
                        "type": "knn_vector",
                        "dimension": EMBEDDING_DIMENSIONS,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 32
                            }
                        }
                    },
                    "emb_audio": {
                        "type": "knn_vector",
                        "dimension": EMBEDDING_DIMENSIONS,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "lucene",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 32
                            }
                        }
                    }
                }
            }
        }
        
        client.indices.create(index=index_name, body=index_body)
        print(f"✓ Created production-grade consolidated index: {index_name}")
        
    except Exception as e:
        print(f"Error creating index: {e}")
        raise


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
            print(f"✓ Successfully read embeddings from S3")
            return result
        except s3_client.exceptions.NoSuchKey:
            continue
        except Exception as e:
            print(f"Error reading from S3 key {key}: {e}")
            continue
    
    raise ValueError(f"Could not find embeddings output in S3 at {bucket}/{key_prefix}")


def validate_embedding(embedding, expected_dim=EMBEDDING_DIMENSIONS):
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


def map_embedding_scope_to_field(scope: str) -> Optional[str]:
    """Map Marengo embedding scope to OpenSearch field name"""
    scope_mapping = {
        'visual': 'emb_visual',
        'audio': 'emb_audio',
        'transcription': 'emb_transcription'
    }
    
    return scope_mapping.get(scope, None)


def extract_frame_at_timestamp(video_path: str, timestamp: float, temp_dir: str) -> Optional[str]:
    """Extract a single frame from video at specified timestamp using ffmpeg"""
    try:
        frame_output = os.path.join(temp_dir, 'thumbnail_frame.jpg')
        
        # Use ffmpeg to extract frame
        cmd = [
            'ffmpeg',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-vf', 'scale=640:360',
            '-q:v', '2',
            '-y',
            frame_output
        ]
        
        print(f"Extracting frame at {timestamp}s using ffmpeg")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(frame_output):
            print(f"✓ Extracted frame: {frame_output}")
            return frame_output
        else:
            print(f"⚠️ ffmpeg failed: {result.stderr[:200]}")
            return None
            
    except FileNotFoundError:
        print(f"✗ ffmpeg not found in Lambda environment")
        return None
    except subprocess.TimeoutExpired:
        print(f"✗ ffmpeg timeout (video may be corrupted)")
        return None
    except Exception as e:
        print(f"✗ Error extracting frame: {e}")
        return None


def upload_frame_to_s3(s3_client, frame_path: str) -> Optional[str]:
    """Upload extracted frame to S3 and return S3 URI"""
    try:
        if not THUMBNAIL_BUCKET:
            print("⚠️ THUMBNAIL_BUCKET not configured, skipping upload")
            return None
        
        # Generate unique thumbnail filename
        thumbnail_name = f"{uuid.uuid4()}.jpg"
        thumbnail_key = f"{THUMBNAIL_PREFIX}{thumbnail_name}"
        
        # Read frame file
        with open(frame_path, 'rb') as f:
            frame_data = f.read()
        
        # Upload to S3
        s3_client.put_object(
            Bucket=THUMBNAIL_BUCKET,
            Key=thumbnail_key,
            Body=frame_data,
            ContentType='image/jpeg'
        )
        
        # Return S3 URI
        s3_uri = f"s3://{THUMBNAIL_BUCKET}/{thumbnail_key}"
        print(f"✓ Uploaded thumbnail to {s3_uri}")
        return s3_uri
        
    except Exception as e:
        print(f"✗ Error uploading frame: {str(e)[:100]}")
        return None


def index_embeddings_to_opensearch_consolidated(opensearch_client, s3_client, embeddings_data: dict,
                                                video_id: str, original_video: dict, part: int, categories: list) -> int:
    """
    Index embeddings into OpenSearch with consolidation and thumbnail generation
    """
    index_name = INDEX_NAME
    
    if 'data' in embeddings_data:
        segments = embeddings_data['data']
    else:
        segments = []
    
    print(f"Found {len(segments)} segments to consolidate")
    
    # Extract video info
    video_name = original_video['key'].split('/')[-1].replace('-', ' ').replace('_', ' ')
    video_s3_uri = f"s3://{original_video['bucket']}/{original_video['key']}"
    
    # Step 1: Group embeddings by clip_id
    clips_by_id = defaultdict(lambda: {
        'metadata': None,
        'embeddings': {}
    })

    video_duration = 0

    for segment in segments:
        if video_duration > 0 and segment.get('startSec') == 0:
            break
        clip_duration = segment.get('endSec', 0) - segment.get('startSec', 0)
        video_duration += clip_duration

    
    for idx, segment in enumerate(segments):
        try:
            embedding = segment.get('embedding', [])
            
            # Validate embedding
            is_valid, validation_msg = validate_embedding(embedding)
            if not is_valid:
                print(f"⚠️ Skipping segment {idx}: {validation_msg}")
                continue
            
            start_time = round(segment.get('startSec', 0), 2)
            end_time = round(segment.get('endSec', 0), 2)
            embedding_scope = segment.get('embeddingOption', 'unknown')
            
            # Generate clip ID
            clip_id = generate_clip_id(video_id, start_time, end_time)
            
            # Store metadata (once per clip)
            if clips_by_id[clip_id]['metadata'] is None:
                clips_by_id[clip_id]['metadata'] = {
                    'video_id': video_id,
                    'video_path': video_s3_uri,
                    'video_name': video_name,
                    'video_duration_sec': round(video_duration, 2),
                    'clip_id': clip_id,
                    'part': part,
                    'timestamp_start': float(start_time),
                    'timestamp_end': float(end_time),
                    'clip_duration': float(end_time - start_time),
                    'clip_text': video_name,
                    'created_at': datetime.utcnow().isoformat(),
                    'categories': categories
                }
            
            # Map scope to field name and store embedding
            field_name = map_embedding_scope_to_field(embedding_scope)
            if field_name:
                clips_by_id[clip_id]['embeddings'][field_name] = embedding
                print(f"  Clip {clip_id[:8]}... - Added {embedding_scope} → {field_name}")
            else:
                print(f"⚠️ Unknown embedding scope: {embedding_scope}")
            
        except Exception as e:
            print(f"Error processing segment {idx}: {e}")
            continue
    
    print(f"✓ Consolidated {len(segments)} segments into {len(clips_by_id)} unique clips")
    
    # ===== Download video ONCE before processing clips =====
    temp_dir = tempfile.mkdtemp()
    video_path = None
    
    try:
        # Download video once for all clips
        video_path = os.path.join(temp_dir, 'video.mp4')
        
        try:
            print(f"Downloading video from s3://{original_video['bucket']}/{original_video['key']}")
            s3_client.download_file(original_video['bucket'], original_video['key'], video_path)
            print(f"✓ Downloaded video to {video_path} (will reuse for all {len(clips_by_id)} clips)")
        except Exception as e:
            print(f"⚠️ Cannot download video: {str(e)[:100]}")
            print(f"  Skipping thumbnail generation for all clips")
            video_path = None
        
        # Step 2: Index consolidated clips with thumbnails
        indexed_count = 0
        
        for clip_id, clip_data in clips_by_id.items():
            try:
                # Build document
                doc = clip_data['metadata'].copy()
                doc.update(clip_data['embeddings'])
                
                # Skip if no embeddings
                if len(clip_data['embeddings']) == 0:
                    print(f"⚠️ Skipping clip {clip_id} - no valid embeddings")
                    continue
                
                # Generate thumbnail using the already-downloaded video
                if video_path and os.path.exists(video_path):
                    thumbnail_uri = generate_thumbnail_from_downloaded_video(
                        s3_client,
                        video_path,
                        doc['timestamp_start']
                    )
                    
                    if thumbnail_uri:
                        doc['thumbnail_path'] = thumbnail_uri
                        print(f"  ✓ Added thumbnail: {thumbnail_uri}")
                    else:
                        doc['thumbnail_path'] = None
                        print(f"  ⚠️ No thumbnail generated")
                else:
                    doc['thumbnail_path'] = None
                    print(f"  ⚠️ Video not available, skipping thumbnail")
                
                # Index document
                response = opensearch_client.index(
                    index=index_name,
                    id=clip_id,
                    body=doc
                )
                
                indexed_count += 1
                
                if indexed_count % 10 == 0:
                    print(f"Indexed {indexed_count}/{len(clips_by_id)} consolidated clips")
                
                # Log details
                modalities = list(clip_data['embeddings'].keys())
                duration = doc['clip_duration']
                print(f"  ✓ Clip {clip_id[:8]}... indexed:")
                print(f"     Duration: {duration:.2f}s")
                print(f"     Modalities ({len(modalities)}): {modalities}")
                
            except Exception as e:
                print(f"Error indexing clip {clip_id}: {e}")
                continue
        
        print(f"✓ Successfully indexed {indexed_count} consolidated clips with thumbnails")
        
        return indexed_count
        
    finally:
        # Cleanup: Delete temporary directory and video file
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"✓ Cleaned up temporary directory")


def generate_thumbnail_from_downloaded_video(s3_client, video_path: str, timestamp: float) -> Optional[str]:
    """
    Generate thumbnail from already-downloaded video at specified timestamp
    Returns S3 URI of generated thumbnail
    """
    try:
        print(f"Generating thumbnail at {timestamp}s from {video_path}")
        
        # Create temporary directory for frame
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Extract frame at timestamp
            frame_path = extract_frame_at_timestamp(video_path, timestamp, temp_dir)
            
            if frame_path:
                # Upload frame to S3
                thumbnail_s3_uri = upload_frame_to_s3(s3_client, frame_path)
                print(f"✓ Generated thumbnail: {thumbnail_s3_uri}")
                return thumbnail_s3_uri
            else:
                print(f"⚠️ Frame extraction failed")
                return None
                
        finally:
            # Cleanup frame temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"✗ Error generating thumbnail: {e}")
        return None
