from fastapi import FastAPI, HTTPException
import json
import boto3
import os
import logging
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from typing import List, Dict, Optional
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Video Search Service", version="2.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://condenast-fe.s3-website-us-east-1.amazonaws.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query_text: str
    video_id: Optional[str] = None  # For targeted video search
    top_k: int = 10
    search_type: str = "hybrid"  # hybrid, vector, text, multimodal


class VideoMetadata(BaseModel):
    video_id: str
    video_path: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    upload_date: Optional[str] = None
    clips_count: int = 0


class VideosListResponse(BaseModel):
    videos: List[VideoMetadata]
    total: int


class SearchResponse(BaseModel):
    query: str
    search_type: str
    total: int
    clips: List[Dict]


# Industry-standard weights for different search types
SEARCH_WEIGHTS = {
    # Hybrid: Balanced between modalities and text matching
    "hybrid": {
        "emb_vis_text": 1.0,
        "emb_vis_image": 1.0,
        "emb_audio": 1.0,
        "text_match": 1.0  # BM25 text matching boost
    },
    # Vector: Pure semantic search across modalities (equal weights)
    "vector": {
        "emb_vis_text": 1.0,
        "emb_vis_image": 1.0,
        "emb_audio": 1.0
    },
    # Multimodal: Text-focused (for text queries)
    "multimodal": {
        "emb_vis_text": 2.0,
        "emb_vis_image": 1.5,
        "emb_audio": 1.0
    }
}


@app.get("/health")
async def health_check():
    """Health check endpoint for ECS task"""
    return {"status": "healthy", "service": "video-search", "version": "2.0.0"}


@app.post("/search", response_model=SearchResponse)
async def search_videos(request: SearchRequest):
    """
    Search videos using industry-standard methods.

    Supported search_type values:
    - hybrid: Combines vector search + text matching (BM25) with balanced weights
    - vector: Pure semantic search across all Marengo modalities (equal weights)
    - text: Text-only BM25 search on clip_text
    - multimodal: Multi-modality weighted search (text-focused, NEW)

    Query Parameters:
    - query_text: Text to search for
    - video_id: (Optional) Filter to specific video
    - top_k: Number of results (default 10)
    - search_type: Search method (default hybrid)
    """
    try:
        query_text = request.query_text
        video_id = request.video_id
        top_k = request.top_k
        search_type = request.search_type

        if not query_text:
            raise HTTPException(status_code=400, detail="query_text is required")

        logger.info(f"Searching for: '{query_text}' (video_id: {video_id}, type: {search_type}, top_k: {top_k})")

        # Initialize clients
        opensearch_client = get_opensearch_client()
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='us-east-1')

        # Generate query embedding using Bedrock Marengo
        query_embedding = generate_text_embedding(bedrock_runtime, query_text)

        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        logger.info(f"Generated embedding with {len(query_embedding)} dimensions")

        # Perform search based on type
        if search_type == "hybrid":
            # Hybrid: Vector + Text matching with balanced weights
            results = hybrid_search(opensearch_client, query_embedding, query_text, video_id, top_k)
        elif search_type == "vector":
            # Vector: Pure semantic search with equal weights
            results = vector_search(opensearch_client, query_embedding, video_id, top_k)
        elif search_type == "text":
            # Text: Pure BM25 text search
            results = text_search(opensearch_client, query_text, video_id, top_k)
        elif search_type == "multimodal":
            # Multimodal: Text-focused multi-modality search
            results = multimodal_search(opensearch_client, query_embedding, video_id, top_k)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search_type: {search_type}. Choose from: hybrid, vector, text, multimodal"
            )

        # Convert S3 paths to presigned URLs
        results = convert_s3_to_presigned_urls(s3_client, results)

        logger.info(f"Found {len(results)} results using {search_type} search")

        return SearchResponse(
            query=query_text,
            search_type=search_type,
            total=len(results),
            clips=results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/in-video", response_model=SearchResponse)
async def search_in_video(request: SearchRequest, video_id: str):
    """
    Search within a specific video using hybrid search (default).
    Perfect for targeted video search with improved relevance.
    """
    try:
        query_text = request.query_text
        top_k = request.top_k
        search_type = request.search_type

        if not query_text:
            raise HTTPException(status_code=400, detail="query_text is required")

        logger.info(f"Searching in video {video_id}: '{query_text}' (type: {search_type}, top_k: {top_k})")

        # Initialize clients
        opensearch_client = get_opensearch_client()
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='us-east-1')

        # Generate query embedding
        query_embedding = generate_text_embedding(bedrock_runtime, query_text)

        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        # Search within specific video
        if search_type == "hybrid":
            results = hybrid_search(opensearch_client, query_embedding, query_text, video_id, top_k)
        elif search_type == "vector":
            results = vector_search(opensearch_client, query_embedding, video_id, top_k)
        elif search_type == "text":
            results = text_search(opensearch_client, query_text, video_id, top_k)
        elif search_type == "multimodal":
            results = multimodal_search(opensearch_client, query_embedding, video_id, top_k)
        else:
            results = hybrid_search(opensearch_client, query_embedding, query_text, video_id, top_k)

        # Convert S3 paths to presigned URLs
        results = convert_s3_to_presigned_urls(s3_client, results)

        logger.info(f"Found {len(results)} results in video {video_id}")

        return SearchResponse(
            query=query_text,
            search_type=search_type,
            total=len(results),
            clips=results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in in-video search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list", response_model=VideosListResponse)
async def list_all_videos():
    """
    Get all unique videos from the OpenSearch consolidated index
    Returns video metadata including S3 paths and clip counts
    """
    try:
        opensearch_client = get_opensearch_client()
        s3_client = boto3.client('s3', region_name='us-east-1')

        # Get all unique videos from consolidated index
        videos = get_all_unique_videos(opensearch_client)

        # Transform to response format
        video_list = []
        for video in videos:
            # Generate presigned URL for private S3 bucket access
            presigned_url = convert_s3_to_presigned_url(s3_client, video['video_path'])

            video_list.append(VideoMetadata(
                video_id=video['video_id'],
                video_path=presigned_url if presigned_url else video['video_path'],
                title=video.get('clip_text') or f"Video {video['video_id'][:8]}",
                thumbnail_url=video.get('thumbnail_url'),
                duration=video.get('duration'),
                upload_date=video.get('upload_date'),
                clips_count=video.get('clips_count', 0)
            ))

        return VideosListResponse(
            videos=video_list,
            total=len(video_list)
        )

    except Exception as e:
        logger.error(f"Error in list_videos: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_index_stats():
    """Get statistics about consolidated index and available search types"""
    try:
        opensearch_client = get_opensearch_client()

        # Get index stats
        stats = opensearch_client.cat.count(index="updated_video_clips", format='json')
        clip_count = int(stats[0]['count'])

        # Get sample document to check modalities
        sample = opensearch_client.search(
            index="updated_video_clips",
            body={"size": 1, "query": {"match_all": {}}}
        )

        modality_info = {}
        if sample['hits']['hits']:
            doc = sample['hits']['hits'][0]['_source']
            marengo_fields = {
                'emb_vis_image': 'visual-image',
                'emb_vis_text': 'visual-text',
                'emb_audio': 'audio'
            }

            for field, label in marengo_fields.items():
                if field in doc:
                    modality_info[label] = {
                        'field': field,
                        'dimension': len(doc.get(field, [])),
                        'present': True
                    }

        return {
            'total_clips': clip_count,
            'marengo_modalities': modality_info,
            'index_name': 'updated_video_clips',
            'structure': 'flat with separate Marengo embedding fields',
            'available_search_types': {
                'hybrid': {
                    'description': 'Vector + Text matching with balanced weights',
                    'weights': SEARCH_WEIGHTS['hybrid']
                },
                'vector': {
                    'description': 'Pure semantic search with equal weights',
                    'weights': SEARCH_WEIGHTS['vector']
                },
                'text': {
                    'description': 'Text-only BM25 search',
                    'weights': None
                },
                'multimodal': {
                    'description': 'Multi-modality weighted search (text-focused)',
                    'weights': SEARCH_WEIGHTS['multimodal']
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

def get_opensearch_client():
    """Initialize OpenSearch Cluster client with AWS authentication"""
    opensearch_host = os.environ.get('OPENSEARCH_CLUSTER_HOST')
    if not opensearch_host:
        raise ValueError("OPENSEARCH_CLUSTER_HOST environment variable not set")

    opensearch_host = opensearch_host.replace('https://', '').replace('http://', '').strip()

    session = boto3.Session()
    credentials = session.get_credentials()

    auth = AWSV4SignerAuth(credentials, 'us-east-1', 'es')

    return OpenSearch(
        hosts=[{'host': opensearch_host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20
    )


def generate_text_embedding(bedrock_runtime, text: str) -> List[float]:
    """Generate embedding for text query using Bedrock Marengo"""
    try:
        request_body = {
            "inputType": "text",
            "inputText": text,
            "textTruncate": "none"
        }

        response = bedrock_runtime.invoke_model(
            modelId="us.twelvelabs.marengo-embed-2-7-v1:0",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response['body'].read())

        if 'data' in result and len(result['data']) > 0:
            return result['data'][0].get('embedding', [])

        return []

    except Exception as e:
        logger.error(f"Error generating text embedding: {e}", exc_info=True)
        return []


def hybrid_search(client, query_embedding: List[float], query_text: str, 
                 video_id: Optional[str], top_k: int) -> List[Dict]:
    """
    Hybrid search: Combines vector search on all Marengo modalities + text matching.
    Industry-standard approach with balanced weights.

    Weights (industry standard):
    - emb_vis_text: 1.8 (visual text/OCR)
    - emb_vis_image: 1.2 (visual images)
    - emb_audio: 0.8 (audio)
    - text_match: 1.5 (BM25 text matching)
    """
    must_clauses = []
    if video_id:
        must_clauses.append({"term": {"video_id": video_id}})

    weights = SEARCH_WEIGHTS["hybrid"]

    # Multi-modality vector search + text matching
    should_clauses = [
        {
            "knn": {
                "emb_vis_text": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_vis_text"]
                }
            }
        },
        {
            "knn": {
                "emb_vis_image": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_vis_image"]
                }
            }
        },
        {
            "knn": {
                "emb_audio": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_audio"]
                }
            }
        },
        {
            "match": {
                "clip_text": {
                    "query": query_text,
                    "fuzziness": "AUTO",
                    "boost": weights["text_match"]
                }
            }
        }
    ]

    search_body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "_source": [
            "clip_id", "video_id", "timestamp_start", "timestamp_end", "clip_text", "video_path"
        ]
    }

    try:
        response = client.search(index="updated_video_clips", body=search_body)
        return parse_search_results(response)
    except Exception as e:
        logger.error(f"Hybrid search error: {e}", exc_info=True)
        return []


def vector_search(client, query_embedding: List[float], video_id: Optional[str], top_k: int) -> List[Dict]:
    """
    Pure vector search: Semantic search across all Marengo modalities with equal weights.
    Industry-standard equal-weight approach.

    Weights (industry standard - equal):
    - emb_vis_text: 1.0
    - emb_vis_image: 1.0
    - emb_audio: 1.0
    """
    must_clauses = []
    if video_id:
        must_clauses.append({"term": {"video_id": video_id}})

    weights = SEARCH_WEIGHTS["vector"]

    # Equal-weight multi-modality k-NN search
    should_clauses = [
        {
            "knn": {
                "emb_vis_text": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_vis_text"]
                }
            }
        },
        {
            "knn": {
                "emb_vis_image": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_vis_image"]
                }
            }
        },
        {
            "knn": {
                "emb_audio": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_audio"]
                }
            }
        }
    ]

    search_body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "_source": [
            "clip_id", "video_id", "timestamp_start", "timestamp_end", "clip_text", "video_path"
        ]
    }

    try:
        response = client.search(index="updated_video_clips", body=search_body)
        return parse_search_results(response)
    except Exception as e:
        logger.error(f"Vector search error: {e}", exc_info=True)
        return []


def text_search(client, query_text: str, video_id: Optional[str], top_k: int) -> List[Dict]:
    """
    Text-only search: Pure BM25 text matching on clip_text field.
    No vector embeddings used.
    """
    must_clauses = [
        {"match": {
            "clip_text": {
                "query": query_text,
                "fuzziness": "AUTO"
            }
        }}
    ]

    if video_id:
        must_clauses.append({"term": {"video_id": video_id}})

    search_body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": must_clauses
            }
        },
        "_source": [
            "clip_id", "video_id", "timestamp_start", "timestamp_end", "clip_text", "video_path"
        ]
    }

    try:
        response = client.search(index="updated_video_clips", body=search_body)
        return parse_search_results(response)
    except Exception as e:
        logger.error(f"Text search error: {e}", exc_info=True)
        return []


def multimodal_search(client, query_embedding: List[float], video_id: Optional[str], top_k: int) -> List[Dict]:
    """
    Multi-modality weighted search: Semantic search focused on text modality.
    Industry-standard approach optimized for text queries.

    Weights (industry standard - text-focused):
    - emb_vis_text: 2.0 (highest)
    - emb_vis_image: 1.5
    - emb_audio: 1.0 (lowest)
    """
    must_clauses = []
    if video_id:
        must_clauses.append({"term": {"video_id": video_id}})

    weights = SEARCH_WEIGHTS["multimodal"]

    should_clauses = [
        {
            "knn": {
                "emb_vis_text": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_vis_text"]
                }
            }
        },
        {
            "knn": {
                "emb_vis_image": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_vis_image"]
                }
            }
        },
        {
            "knn": {
                "emb_audio": {
                    "vector": query_embedding,
                    "k": top_k,
                    "boost": weights["emb_audio"]
                }
            }
        }
    ]

    search_body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "_source": [
            "clip_id", "video_id", "timestamp_start", "timestamp_end", "clip_text", "video_path"
        ]
    }

    try:
        response = client.search(index="updated_video_clips", body=search_body)
        return parse_search_results(response)
    except Exception as e:
        logger.error(f"Multimodal search error: {e}", exc_info=True)
        return []


def get_all_unique_videos(client) -> List[Dict]:
    """Get all unique videos from consolidated index"""
    search_body = {
        "size": 0,
        "aggs": {
            "unique_videos": {
                "terms": {
                    "field": "video_id",
                    "size": 10000
                },
                "aggs": {
                    "video_metadata": {
                        "top_hits": {
                            "size": 1,
                            "_source": ["video_id", "video_path", "clip_text"]
                        }
                    },
                    "clip_count": {
                        "cardinality": {
                            "field": "clip_id"
                        }
                    }
                }
            }
        }
    }

    try:
        response = client.search(index="updated_video_clips", body=search_body)

        videos = []
        for bucket in response['aggregations']['unique_videos']['buckets']:
            video_data = bucket['video_metadata']['hits']['hits'][0]['_source']
            video_data['clips_count'] = bucket['clip_count']['value']
            videos.append(video_data)

        return videos

    except Exception as e:
        logger.error(f"Error fetching unique videos: {e}", exc_info=True)
        return []


def convert_s3_to_presigned_urls(s3_client, results: List[Dict], expiration: int = 3600) -> List[Dict]:
    """Convert S3 paths to presigned URLs in video_path field"""
    for result in results:
        video_path = result.get('video_path', '')

        if video_path.startswith('s3://'):
            try:
                s3_parts = video_path.replace('s3://', '').split('/', 1)
                bucket = s3_parts[0]
                key = s3_parts[1] if len(s3_parts) > 1 else ''

                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=expiration
                )

                result['video_path'] = presigned_url

            except Exception as e:
                logger.warning(f"Error generating presigned URL for {video_path}: {e}")
                pass

    return results


def convert_s3_to_presigned_url(s3_client, video_path: str, expiration: int = 3600) -> Optional[str]:
    """Convert single S3 path to presigned URL"""
    if not video_path.startswith('s3://'):
        return None

    try:
        s3_parts = video_path.replace('s3://', '').split('/', 1)
        bucket = s3_parts[0]
        key = s3_parts[1] if len(s3_parts) > 1 else ''

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )

        return presigned_url

    except Exception as e:
        logger.warning(f"Error generating presigned URL for {video_path}: {e}")
        return None


def parse_search_results(response: Dict) -> List[Dict]:
    """Parse OpenSearch response into results list"""
    results = []

    for hit in response['hits']['hits']:
        source = hit['_source']

        result = {
            'clip_id': source.get('clip_id'),
            'video_id': source.get('video_id'),
            'video_path': source.get('video_path'),
            'timestamp_start': source.get('timestamp_start'),
            'timestamp_end': source.get('timestamp_end'),
            'clip_text': source.get('clip_text'),
            'score': hit.get('_score')
        }

        results.append(result)

    return results


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
