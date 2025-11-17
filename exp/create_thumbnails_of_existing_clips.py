import boto3
import json
import logging
import os
from typing import List, Dict, Optional, Tuple
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
import uuid
import subprocess
import tempfile
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
INDEX_NAME = "video_clips_consolidated"
PEGASUS_MODEL_ID = "amazon.titan-text-express-v1:0"  # Using Bedrock Titan for text summarization
THUMBNAIL_BUCKET = os.environ.get('THUMBNAIL_BUCKET', 'condenast-processed-useast1-943143228843-dev')
THUMBNAIL_PREFIX = 'thumbnails/'


class OpenSearchConnector:
    """Handles OpenSearch connection and operations"""
    
    def __init__(self):
        self.client = self._initialize_client()
    
    def _initialize_client(self) -> OpenSearch:
        """Initialize OpenSearch client with AWS authentication from .env"""
        try:
            opensearch_host = os.environ.get('OPENSEARCH_CLUSTER_HOST')
            if not opensearch_host:
                raise ValueError("OPENSEARCH_CLUSTER_HOST environment variable not set in .env file")
            
            opensearch_host = opensearch_host.replace('https://', '').replace('http://', '').strip()
            
            # Load AWS credentials from environment variables (.env file)
            aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
            aws_region = os.environ.get('AWS_REGION', 'us-east-1')
            
            if not aws_access_key_id or not aws_secret_access_key:
                raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env file")
            
            # Create session with explicit credentials
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region_name=aws_region
            )
            credentials = session.get_credentials()
            
            auth = AWSV4SignerAuth(credentials, aws_region, 'es')
            
            client = OpenSearch(
                hosts=[{'host': opensearch_host, 'port': 443}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                pool_maxsize=20
            )
            
            logger.info(f"✓ Successfully connected to OpenSearch cluster at {opensearch_host}")
            return client
            
        except Exception as e:
            logger.error(f"✗ Failed to connect to OpenSearch: {e}", exc_info=True)
            raise
    
    def test_connection(self) -> bool:
        """Test OpenSearch connection"""
        try:
            info = self.client.info()
            logger.info(f"✓ OpenSearch cluster info: {info['version']['number']}")
            return True
        except Exception as e:
            logger.error(f"✗ Connection test failed: {e}")
            return False
    
    def get_all_clips(self, limit: int = 10000) -> List[Dict]:
        """Fetch all clips from OpenSearch index"""
        try:
            search_body = {
                "size": limit,
                "query": {
                    "match_all": {}
                },
                "_source": ["clip_id", "video_id", "video_path", "clip_text", 
                           "timestamp_start", "timestamp_end", "clip_duration", "video_name"]
            }
            
            response = self.client.search(index=INDEX_NAME, body=search_body)
            clips = []
            
            for hit in response['hits']['hits']:
                clip = hit['_source']
                clip['_id'] = hit['_id']
                clips.append(clip)
            
            logger.info(f"✓ Retrieved {len(clips)} clips from OpenSearch")
            return clips
            
        except Exception as e:
            logger.error(f"✗ Error fetching clips: {e}", exc_info=True)
            return []
    
    def update_clip_summary(self, clip_id: str, summary: str, thumbnail_s3_uri: str) -> bool:
        """Update clip document with generated summary and thumbnail S3 URI"""
        try:
            update_body = {
                "doc": {
                    "clip_text": summary,
                    "thumbnail_path": thumbnail_s3_uri
                }
            }
            
            self.client.update(index=INDEX_NAME, id=clip_id, body=update_body)
            logger.info(f"✓ Updated clip {clip_id} with summary and thumbnail S3 URI: {thumbnail_s3_uri}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error updating clip {clip_id}: {e}")
            return False


class PegasusTextSummarizer:
    """Handles text summarization using Bedrock models"""
    
    def __init__(self):
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
    
    def summarize_text(self, text: str, max_length: int = 150) -> Optional[str]:
        """Generate summary using Bedrock Titan model"""
        try:
            if not text or len(text.strip()) == 0:
                logger.warning("Empty text provided for summarization")
                return None
            
            # Truncate text if too long
            if len(text) > 2000:
                text = text[:2000]
            
            prompt = f"""Summarize the following video clip description in {max_length} words or less. 
Be concise and capture the main content:

{text}

Summary:"""
            
            request_body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 256,
                    "temperature": 0.7,
                    "topP": 0.9
                }
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=PEGASUS_MODEL_ID,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            result = json.loads(response['body'].read())
            
            if 'results' in result and len(result['results']) > 0:
                summary = result['results'][0]['outputText'].strip()
                logger.info(f"✓ Generated summary: {summary[:100]}...")
                return summary
            
            return None
            
        except Exception as e:
            logger.error(f"✗ Error generating summary: {e}", exc_info=True)
            return None


class ThumbnailGenerator:
    """Handles thumbnail generation from S3 video URIs with caching"""
    
    def __init__(self):
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
        aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        self.s3_client = boto3.client(
            's3',
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token
        )
        
        # Cache for downloaded videos: {s3_uri -> local_path}
        self.video_cache = {}
        self.cache_dir = tempfile.mkdtemp(prefix='video_cache_')
        logger.info(f"✓ Created video cache directory: {self.cache_dir}")
    
    def __del__(self):
        """Cleanup cache directory on object destruction"""
        if hasattr(self, 'cache_dir') and os.path.exists(self.cache_dir):
            try:
                shutil.rmtree(self.cache_dir)
                logger.info(f"Cleaned up video cache directory: {self.cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup cache directory: {e}")
    
    def generate_thumbnail_from_s3(self, s3_uri: str, timestamp: float = 0.0) -> Optional[str]:
        """
        Generate thumbnail from S3 video URI at start timestamp
        Extracts frame using ffmpeg and stores S3 URI
        Uses caching to avoid re-downloading same videos
        """
        try:
            if not s3_uri.startswith('s3://'):
                logger.warning(f"Invalid S3 URI: {s3_uri}")
                return None
            
            # Parse S3 URI
            s3_parts = s3_uri.replace('s3://', '').split('/', 1)
            bucket = s3_parts[0]
            key = s3_parts[1] if len(s3_parts) > 1 else ''
            
            logger.info(f"Generating thumbnail for: s3://{bucket}/{key} at timestamp {timestamp}s")
            
            # Check cache first
            if s3_uri in self.video_cache:
                video_path = self.video_cache[s3_uri]
                logger.info(f"✓ Using cached video: {video_path}")
            else:
                # Download video from S3 to cache directory
                video_filename = f"{len(self.video_cache)}_{os.path.basename(key)}"
                video_path = os.path.join(self.cache_dir, video_filename)
                
                if not self._download_video_from_s3(bucket, key, video_path):
                    logger.warning("Failed to download video, creating placeholder")
                    thumbnail = self._create_placeholder_thumbnail(key, timestamp)
                    return self._upload_thumbnail_to_s3(thumbnail, bucket, key)
                
                # Store in cache
                self.video_cache[s3_uri] = video_path
                logger.info(f"✓ Cached video: {s3_uri}")
            
            # Create temporary directory for frame extraction
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Extract frame at start timestamp
                frame_path = self._extract_frame_at_timestamp(video_path, timestamp, temp_dir)
                
                if frame_path:
                    # Upload frame to S3 and get S3 URI
                    thumbnail_s3_uri = self._upload_frame_to_s3(frame_path, bucket, key)
                    logger.info(f"✓ Generated thumbnail: {thumbnail_s3_uri}")
                    return thumbnail_s3_uri
                else:
                    logger.warning("Frame extraction failed, creating placeholder")
                    thumbnail = self._create_placeholder_thumbnail(key, timestamp)
                    return self._upload_thumbnail_to_s3(thumbnail, bucket, key)
            finally:
                # Cleanup temporary directory for frame extraction
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            
        except Exception as e:
            logger.error(f"✗ Error generating thumbnail: {e}", exc_info=True)
            return None
    
    def _download_video_from_s3(self, bucket: str, key: str, local_path: str) -> bool:
        """Download video from S3 to local temporary directory"""
        try:
            logger.info(f"Downloading video from s3://{bucket}/{key}")
            self.s3_client.download_file(bucket, key, local_path)
            logger.info(f"✓ Downloaded video to {local_path}")
            return True
        except Exception as e:
            logger.warning(f"⚠ Cannot download video (403 Forbidden or invalid credentials): {str(e)[:100]}")
            logger.warning(f"  Bucket: {bucket}, Key: {key}")
            logger.warning(f"  Check AWS credentials and S3 bucket permissions")
            return False
    
    def _extract_frame_at_timestamp(self, video_path: str, timestamp: float, temp_dir: str) -> Optional[str]:
        """Extract a single frame from video at specified timestamp using ffmpeg"""
        try:
            frame_output = os.path.join(temp_dir, 'thumbnail_frame.jpg')
            
            # Use ffmpeg to extract frame at timestamp
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-vf', 'scale=640:360',
                '-y',
                frame_output
            ]
            
            logger.info(f"Extracting frame at {timestamp}s using ffmpeg")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(frame_output):
                logger.info(f"✓ Extracted frame: {frame_output}")
                return frame_output
            else:
                logger.warning(f"ffmpeg failed: {result.stderr}")
                return None
                
        except FileNotFoundError:
            logger.error(f"✗ ffmpeg not found: Install ffmpeg and add to PATH")
            logger.error(f"  Windows: choco install ffmpeg")
            logger.error(f"  macOS: brew install ffmpeg")
            logger.error(f"  Linux: sudo apt-get install ffmpeg")
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg timeout while extracting frame (video may be corrupted)")
            return None
        except Exception as e:
            logger.error(f"✗ Error extracting frame: {e}")
            return None
    
    def _upload_frame_to_s3(self, frame_path: str, source_bucket: str, source_key: str) -> Optional[str]:
        """Upload extracted frame to S3 and return S3 URI"""
        try:
            # Generate unique thumbnail filename
            thumbnail_name = f"{uuid.uuid4()}.jpg"
            thumbnail_key = f"{THUMBNAIL_PREFIX}{thumbnail_name}"
            
            # Read frame file
            with open(frame_path, 'rb') as f:
                frame_data = f.read()
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=THUMBNAIL_BUCKET,
                Key=thumbnail_key,
                Body=frame_data,
                ContentType='image/jpeg'
            )
            
            # Return S3 URI
            s3_uri = f"s3://{THUMBNAIL_BUCKET}/{thumbnail_key}"
            logger.info(f"✓ Uploaded thumbnail to {s3_uri}")
            return s3_uri
            
        except Exception as e:
            error_msg = str(e)
            if 'InvalidAccessKeyId' in error_msg or 'SignatureDoesNotMatch' in error_msg:
                logger.error(f"✗ Invalid AWS credentials: Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
            elif '403' in error_msg or 'Forbidden' in error_msg:
                logger.error(f"✗ Access denied to S3 bucket '{THUMBNAIL_BUCKET}': Check bucket permissions")
            else:
                logger.error(f"✗ Error uploading frame: {error_msg[:100]}")
            return None
    
    def _create_placeholder_thumbnail(self, video_name: str, timestamp: float) -> Image.Image:
        """Create a placeholder thumbnail image"""
        try:
            # Create a simple image with video info
            img = Image.new('RGB', (320, 180), color=(73, 109, 137))
            logger.info(f"Created placeholder thumbnail for {video_name} at {timestamp}s")
            return img
            
        except Exception as e:
            logger.error(f"✗ Error creating placeholder thumbnail: {e}")
            return None
    
    def _upload_thumbnail_to_s3(self, thumbnail: Image.Image, source_bucket: str, source_key: str) -> Optional[str]:
        """Upload placeholder thumbnail to S3 and return S3 URI"""
        try:
            # Generate unique thumbnail filename
            thumbnail_name = f"{uuid.uuid4()}.jpg"
            thumbnail_key = f"{THUMBNAIL_PREFIX}{thumbnail_name}"
            
            # Convert image to bytes
            img_byte_arr = BytesIO()
            thumbnail.save(img_byte_arr, format='JPEG')
            img_byte_arr.seek(0)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=THUMBNAIL_BUCKET,
                Key=thumbnail_key,
                Body=img_byte_arr.getvalue(),
                ContentType='image/jpeg'
            )
            
            # Return S3 URI
            s3_uri = f"s3://{THUMBNAIL_BUCKET}/{thumbnail_key}"
            logger.info(f"✓ Uploaded placeholder thumbnail to {s3_uri}")
            return s3_uri
            
        except Exception as e:
            error_msg = str(e)
            if 'InvalidAccessKeyId' in error_msg or 'SignatureDoesNotMatch' in error_msg:
                logger.error(f"✗ Invalid AWS credentials: Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
            elif '403' in error_msg or 'Forbidden' in error_msg:
                logger.error(f"✗ Access denied to S3 bucket '{THUMBNAIL_BUCKET}': Check bucket permissions")
            else:
                logger.error(f"✗ Error uploading thumbnail: {error_msg[:100]}")
            return None


class ClipProcessor:
    """Main processor that orchestrates summarization and thumbnail generation"""
    
    def __init__(self):
        self.opensearch = OpenSearchConnector()
        self.summarizer = PegasusTextSummarizer()
        self.thumbnail_gen = ThumbnailGenerator()
    
    def process_all_clips(self, batch_size: int = 10) -> Dict:
        """Process all clips: generate summaries and thumbnails"""
        try:
            clips = self.opensearch.get_all_clips()
            
            if not clips:
                logger.warning("No clips found to process")
                return {"processed": 0, "failed": 0, "results": []}
            
            results = []
            processed_count = 0
            failed_count = 0
            
            logger.info(f"Starting processing of {len(clips)} clips...")
            
            for idx, clip in enumerate(clips, 1):
                logger.info(f"\n[{idx}/{len(clips)}] Processing clip: {clip.get('clip_id', 'unknown')}")
                
                try:
                    # # Generate summary
                    # summary = self.summarizer.summarize_text(clip.get('clip_text', ''))
                    
                    # Generate thumbnail
                    thumbnail_url = self.thumbnail_gen.generate_thumbnail_from_s3(
                        clip.get('video_path', ''),
                        clip.get('timestamp_start', 0.0)
                    )
                    
                    # Update OpenSearch document
                    if thumbnail_url:
                        success = self.opensearch.update_clip_summary(
                            clip['_id'],
                            clip.get('clip_text', ''),  # Keep existing text
                            thumbnail_url
                        )
                        
                        if success:
                            processed_count += 1
                            results.append({
                                "clip_id": clip.get('clip_id'),
                                "thumbnail_url": thumbnail_url,
                                "status": "success"
                            })
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                        logger.warning(f"Failed to generate thumbnail for clip {clip.get('clip_id')}")
                
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing clip {clip.get('clip_id')}: {e}")
            
            summary_stats = {
                "total_clips": len(clips),
                "processed": processed_count,
                "failed": failed_count,
                "results": results
            }
            
            logger.info(f"\n✓ Processing complete: {processed_count} succeeded, {failed_count} failed")
            return summary_stats
            
        except Exception as e:
            logger.error(f"✗ Error in process_all_clips: {e}", exc_info=True)
            return {"processed": 0, "failed": 0, "results": []}
    
    def process_single_clip(self, clip_id: str) -> Optional[Dict]:
        """Process a single clip by ID"""
        try:
            # Fetch clip from OpenSearch
            search_body = {
                "query": {
                    "term": {
                        "clip_id.keyword": clip_id
                    }
                }
            }
            
            response = self.opensearch.client.search(index=INDEX_NAME, body=search_body)
            
            if not response['hits']['hits']:
                logger.warning(f"Clip {clip_id} not found")
                return None
            
            clip = response['hits']['hits'][0]['_source']
            clip_opensearch_id = response['hits']['hits'][0]['_id']
            
            logger.info(f"Processing single clip: {clip_id}")
            
            # # Generate summary
            # summary = self.summarizer.summarize_text(clip.get('clip_text', ''))
            
            # Generate thumbnail
            thumbnail_url = self.thumbnail_gen.generate_thumbnail_from_s3(
                clip.get('video_path', ''),
                clip.get('timestamp_start', 0.0)
            )
            
            # Update OpenSearch
            if thumbnail_url:
                self.opensearch.update_clip_summary(clip_opensearch_id, clip.get('clip_text', ''), thumbnail_url)
                
                return {
                    "clip_id": clip_id,
                    "thumbnail_url": thumbnail_url,
                    "status": "success"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"✗ Error processing single clip: {e}", exc_info=True)
            return None


# Testing Functions
def test_opensearch_connection():
    """Test OpenSearch connection"""
    logger.info("\n=== Testing OpenSearch Connection ===")
    try:
        connector = OpenSearchConnector()
        is_connected = connector.test_connection()
        
        if is_connected:
            logger.info("✓ OpenSearch connection test PASSED")
            return True
        else:
            logger.error("✗ OpenSearch connection test FAILED")
            return False
            
    except Exception as e:
        logger.error(f"✗ Connection test error: {e}")
        return False


def test_fetch_clips():
    """Test fetching clips from OpenSearch"""
    logger.info("\n=== Testing Fetch Clips ===")
    try:
        connector = OpenSearchConnector()
        clips = connector.get_all_clips(limit=5)
        
        if clips:
            logger.info(f"✓ Successfully fetched {len(clips)} clips")
            for clip in clips[:2]:
                logger.info(f"  - Clip ID: {clip.get('clip_id')}, Video: {clip.get('video_name')}")
            return True
        else:
            logger.warning("No clips found")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error fetching clips: {e}")
        return False


def test_summarization():
    """Test Pegasus summarization"""
    logger.info("\n=== Testing Text Summarization ===")
    try:
        summarizer = PegasusTextSummarizer()
        
        test_text = "This is a test video clip about a beautiful sunset over the ocean. The video shows waves crashing on the beach with golden light reflecting off the water. Birds are flying in the sky as the sun sets below the horizon."
        
        summary = summarizer.summarize_text(test_text)
        
        if summary:
            logger.info(f"✓ Summarization successful")
            logger.info(f"  Original: {test_text[:80]}...")
            logger.info(f"  Summary: {summary}")
            return True
        else:
            logger.error("✗ Summarization failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error in summarization test: {e}")
        return False


def test_thumbnail_generation():
    """Test thumbnail generation"""
    logger.info("\n=== Testing Thumbnail Generation ===")
    try:
        thumbnail_gen = ThumbnailGenerator()
        
        # Test with a sample S3 URI (you should replace with actual video)
        test_s3_uri = "s3://condenast-videos/sample-video.mp4"
        
        logger.info(f"Testing with S3 URI: {test_s3_uri}")
        
        # This will create a placeholder for now
        thumbnail_url = thumbnail_gen.generate_thumbnail_from_s3(test_s3_uri, timestamp=0.0)
        
        if thumbnail_url:
            logger.info(f"✓ Thumbnail generation successful")
            logger.info(f"  Thumbnail URL: {thumbnail_url[:80]}...")
            return True
        else:
            logger.warning("⚠ Thumbnail generation returned None (may need video processing setup)")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error in thumbnail test: {e}")
        return False


def run_all_tests():
    """Run all connection and functionality tests"""
    logger.info("\n" + "="*60)
    logger.info("RUNNING ALL TESTS")
    logger.info("="*60)
    
    tests = [
        ("OpenSearch Connection", test_opensearch_connection),
        ("Fetch Clips", test_fetch_clips),
        ("Text Summarization", test_summarization),
        ("Thumbnail Generation", test_thumbnail_generation),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            run_all_tests()
        
        elif command == "process-all":
            processor = ClipProcessor()
            results = processor.process_all_clips()
            logger.info(f"\nProcessing Results: {json.dumps(results, indent=2)}")
        
        elif command == "process-single" and len(sys.argv) > 2:
            clip_id = sys.argv[2]
            processor = ClipProcessor()
            result = processor.process_single_clip(clip_id)
            logger.info(f"\nSingle Clip Result: {json.dumps(result, indent=2)}")
        
        else:
            logger.info("Usage:")
            logger.info("  python pegasus_thumbnail_processor.py test              # Run all tests")
            logger.info("  python pegasus_thumbnail_processor.py process-all       # Process all clips")
            logger.info("  python pegasus_thumbnail_processor.py process-single <clip_id>  # Process single clip")
    
    else:
        # Default: run tests
        run_all_tests()
