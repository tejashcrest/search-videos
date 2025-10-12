from twelvelabs import TwelveLabs
from twelvelabs.embed import TasksStatusResponse
from typing import List, Dict
import os
import time

import boto3
import json
from typing import List

from dotenv import load_dotenv

load_dotenv()

class BedrockClient:
    def __init__(self, region: str = "us-east-1"):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
    
    def generate_answer(self, context: str, question: str) -> str:
        """Generate answer using Bedrock LLM (Claude or GPT OSS)"""
        try:
            prompt = f"""Based on the following video clips:

{context}

Question: {question}

Provide a detailed answer with specific timestamps where relevant."""

            response = self.bedrock_runtime.invoke_model(
                modelId='openai.gpt-oss-120b-1:0',
                body=json.dumps({
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "max_output_tokens": 500,
                    "temperature": 0.7
                })
            )
            
            result = json.loads(response['body'].read())
            return result['output'][0]['content'][0]['text']
        
        except Exception as e:
            print(f"Error generating answer: {e}")
            return f"Error: {str(e)}"



class TwelveLabsClient:
    def __init__(self):
        api_key = os.getenv('TWELVELABS_API_KEY')
        if not api_key:
            raise ValueError("TWELVELABS_API_KEY environment variable not set")
        
        self.client = TwelveLabs(api_key=api_key)
    
    def generate_video_embeddings(self, video_path: str) -> List[Dict]:
        """Generate embeddings for video using Marengo"""
        try:
            # Create embedding task
            task = self.client.embed.tasks.create(
                model_name="Marengo-retrieval-2.7",
                video_url=video_path
            )
            
            print(f"Created task: {task.id}")
            
            # Wait for task completion
            task = self._wait_for_task(task.id)
            
            if task.status != "ready":
                print(f"Task failed with status: {task.status}")
                return []
            
            # Retrieve embeddings
            embeddings = []
            task_result = self.client.embed.tasks.retrieve(task.id)
            
            # Process video embeddings
            for segment in task_result.video_embedding.segments:
                print(segment)
                embeddings.append({
                    "start_offset_sec": segment.start_offset_sec,
                    "end_offset_sec": segment.end_offset_sec,
                    "embedding_scope": segment.embedding_scope,
                    "embedding": segment.float_
                })
            
            return embeddings
        
        except Exception as e:
            print(f"Error generating video embeddings: {e}")
            return []
    
    def generate_text_embedding(self, text: str) -> List[float]:
        """Generate embedding for text query using Marengo"""
        try:
            result = self.client.embed.create(
                model_name="Marengo-retrieval-2.7",
                text=text,
                text_truncate="none"
            )
            
            print(result)

            if result.text_embedding and result.text_embedding.segments:
                return result.text_embedding.segments[0].float_
            
            return []
        
        except Exception as e:
            print(f"Error generating text embedding: {e}")
            return []
    
    def _wait_for_task(self, task_id: str, max_wait: int = 600) -> TasksStatusResponse:
        """Poll task until completion"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            task = self.client.embed.tasks.retrieve(task_id)
            
            if task.status in ["ready", "failed"]:
                return task
            
            print(f"Task status: {task.status}")
            time.sleep(10)
        
        raise TimeoutError(f"Task {task_id} did not complete within {max_wait} seconds")

from opensearchpy import OpenSearch
from typing import List, Dict
import os

class OpenSearchClient:
    def __init__(self):
        host = os.getenv('OPENSEARCH_HOST', 'localhost')
        port = int(os.getenv('OPENSEARCH_PORT', 9200))
        username = os.getenv('OPENSEARCH_USERNAME', 'admin')
        password = os.getenv('OPENSEARCH_PASSWORD', 'Jod123@@123!')
        
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(username, password),
            http_compress=True,
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        self._create_index_if_not_exists()
    
    def _create_index_if_not_exists(self):
        """Create video clips index with k-NN"""
        index_name = "video_clips"
        
        if not self.client.indices.exists(index=index_name):
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "video_id": {"type": "keyword"},
                        "video_path": {"type": "keyword"},
                        "timestamp_start": {"type": "float"},
                        "timestamp_end": {"type": "float"},
                        "clip_text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 1024,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "lucene",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 16
                                }
                            }
                        }
                    }
                }
            }
            
            self.client.indices.create(index=index_name, body=index_body)
            print(f"Created index: {index_name}")
    
    def index_clip(self, video_id: str, video_path: str, 
                   timestamp_start: float, timestamp_end: float,
                   embedding: List[float], clip_text: str = ""):
        """Index a video clip with embedding"""
        doc = {
            "video_id": video_id,
            "video_path": video_path,
            "timestamp_start": timestamp_start,
            "timestamp_end": timestamp_end,
            "clip_text": clip_text,
            "embedding": embedding
        }
        
        response = self.client.index(
            index="video_clips",
            body=doc
        )
        return response
    
    def search_similar_clips(self, query_embedding: List[float], 
                            top_k: int = 10) -> List[Dict]:
        """Search for similar video clips using k-NN"""
        search_body = {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k
                    }
                }
            },
            "_source": ["video_id", "video_path", "timestamp_start", 
                       "timestamp_end", "clip_text"]
        }
        
        response = self.client.search(
            index="video_clips",
            body=search_body
        )
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['score'] = hit['_score']
            results.append(result)
        
        return results
    
    def hybrid_search(self, query_embedding: List[float], 
                     text_query: str, top_k: int = 10) -> List[Dict]:
        """Hybrid search combining vector and keyword search"""
        search_body = {
            "size": top_k,
            "query": {
                "hybrid": {
                    "queries": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_embedding,
                                    "k": top_k
                                }
                            }
                        },
                        {
                            "match": {
                                "clip_text": text_query
                            }
                        }
                    ]
                }
            }
        }
        
        response = self.client.search(
            index="video_clips",
            body=search_body
        )
        
        results = []
        for hit in response['hits']['hits']:
            result = hit['_source']
            result['score'] = hit['_score']
            results.append(result)
        
        return results

