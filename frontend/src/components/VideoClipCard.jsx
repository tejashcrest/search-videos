import React from 'react';
import { Play, Clock, TrendingUp, Loader2 } from 'lucide-react';
import { formatTimestamp } from '../utils/formatTime';
import { use_thumbnail } from '../hooks/useThumbnail';

const VideoClipCard = ({ clip, onClick }) => {
  const { video_id, video_path, timestamp_start, timestamp_end, clip_text, score } = clip;
  
  const confidence_level = score > 0.8 ? 'HIGH' : score > 0.5 ? 'MEDIUM' : 'LOW';
  const confidence_color = score > 0.8 ? 'bg-green-100 text-green-700' : score > 0.5 ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700';

  // Load thumbnail from video
  const { thumbnail, isLoading: thumbnailLoading, error: thumbnailError } = use_thumbnail(
    video_path, 
    video_id, 
    timestamp_start
  );

  return (
    <div 
      className="clip-card group"
      onClick={() => onClick(clip)}
    >
      {/* Video Thumbnail */}
      <div className="relative h-48 bg-gray-900 flex items-center justify-center overflow-hidden">
        {/* Loading state */}
        {thumbnailLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
            <Loader2 size={40} className="text-white animate-spin" />
          </div>
        )}
        
        {/* Error state */}
        {thumbnailError && !thumbnail && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-800 text-white p-4">
            <div className="text-red-400 text-sm text-center mb-2">
              Unable to load thumbnail
            </div>
            <div className="text-xs text-gray-400 text-center">
              CORS not enabled on video
            </div>
          </div>
        )}
        
        {/* Actual thumbnail */}
        {thumbnail && (
          <img 
            src={thumbnail} 
            alt={`Thumbnail at ${formatTimestamp(timestamp_start)}`}
            className="absolute inset-0 w-full h-full object-cover"
            loading="lazy"
          />
        )}
        
        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-all duration-300" />
        
        {/* Play button overlay */}
        <div className="relative z-10 w-16 h-16 bg-white/90 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-lg">
          <Play size={28} className="text-primary-600 ml-1" fill="currentColor" />
        </div>
        
        {/* Confidence badge */}
        <div className={`absolute top-3 left-3 px-3 py-1 rounded-full text-xs font-semibold ${confidence_color}`}>
          {confidence_level}
        </div>
        
        {/* Timestamp overlay */}
        <div className="absolute bottom-3 right-3 px-3 py-1 bg-black/70 text-white text-sm rounded-lg font-medium backdrop-blur-sm">
          {formatTimestamp(timestamp_start)} - {formatTimestamp(timestamp_end)}
        </div>
      </div>
      
      {/* Card content */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <Clock size={16} />
            <span>Duration: {Math.round(timestamp_end - timestamp_start)}s</span>
          </div>
          
          <div className="flex items-center gap-1 text-primary-600 text-sm font-medium">
            <TrendingUp size={16} />
            <span>{(score * 100).toFixed(1)}%</span>
          </div>
        </div>
        
        <p className="text-gray-600 text-sm line-clamp-2">
          {clip_text || 'Video clip segment'}
        </p>
        
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-400 truncate">
            Video ID: {video_id}
          </p>
        </div>
      </div>
    </div>
  );
};

export default VideoClipCard;
