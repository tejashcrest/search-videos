from strands import Agent, tool
from clients import TwelveLabsClient, BedrockClient, OpenSearchClient
from typing import List, Dict

class VideoSearchAgent:
    def __init__(self):
        self.bedrock = BedrockClient()
        self.twelvelabs = TwelveLabsClient()
        self.opensearch = OpenSearchClient()
        
        # Initialize Strands agent with instance method tools
        self.agent = Agent(
            name="VideoSearchAgent",
            tools=[
                self.search_videos,
                self.get_video_summary
            ]
        )

    @tool
    def search_videos(self, query: str, top_k: int = 10) -> List[Dict]:
        """Tool: Search for videos using TwelveLabs"""
        # Generate query embedding via TwelveLabs
        query_embedding = self.twelvelabs.generate_text_embedding(query)
        
        if not query_embedding:
            return []
        
        # Search in OpenSearch
        results = self.opensearch.search_similar_clips(query_embedding, top_k)
        
        return results

    @tool
    def get_video_summary(self, clips: List[Dict]) -> str:
        """Tool: Generate summary from clips using Bedrock"""
        context = self._format_clips_for_llm(clips)
        summary = self.bedrock.generate_answer(context, "Provide a summary of these video clips")
        return summary
    
    def answer_question(self, question: str) -> Dict:
        """Main method: Answer user question about videos"""
        # Search for relevant clips
        clips = self.search_videos(question, top_k=5)
        
        if not clips:
            return {
                "answer": "No relevant video clips found.",
                "clips": []
            }
        
        # Format context for LLM
        context = self._format_clips_for_llm(clips)
        
        # Generate answer via Bedrock
        answer = self.bedrock.generate_answer(context, question)
        
        return {
            "answer": answer,
            "clips": clips
        }
    
    def _format_clips_for_llm(self, clips: List[Dict]) -> str:
        """Format clips for LLM context"""
        formatted = []
        for i, clip in enumerate(clips, 1):
            formatted.append(
                f"Clip {i}:\n"
                f"  Video: {clip['video_id']}\n"
                f"  Time: {clip['timestamp_start']:.1f}s - {clip['timestamp_end']:.1f}s\n"
                f"  Content: {clip.get('clip_text', 'N/A')}\n"
                f"  Relevance Score: {clip.get('score', 0):.3f}"
            )
        
        return "\n\n".join(formatted)
