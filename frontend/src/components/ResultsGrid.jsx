import VideoClipCard from './VideoClipCard';
import { FileVideo } from 'lucide-react';

const ResultsGrid = ({ clips, total, query, onClipClick, from }) => {
  if (!clips || clips.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-gray-100 rounded-full mb-4">
          <FileVideo size={40} className="text-gray-400" />
        </div>
        <h3 className="text-xl font-semibold text-gray-700 mb-2">No results found</h3>
        <p className="text-gray-500">
          {query ? `No video clips match "${query}"` : 'Try searching for something'}
        </p>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Results grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {clips.map((clip, index) => (
          <div key={`${clip.video_id}-${clip.timestamp_start}-${index}`} className="flex justify-center">
            <div className="w-full max-w-md">
              <VideoClipCard
                clip={clip}
                onClick={onClipClick}
                from={from}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultsGrid;
