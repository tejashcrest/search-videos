import React, { useRef, useState, useCallback } from 'react';
import { Loader2, Play } from 'lucide-react';
import { formatTimestamp } from '../utils/formatTime';
import { use_thumbnail } from '../hooks/useThumbnail';

const VideoClipCardMarengo3 = ({ clip, onClick, index }) => {
  const {
    video_id,
    video_path,
    timestamp_start,
    timestamp_end,
    clip_text,
    score,
    presigned_url,
    thumbnail_path,
    video_name,
    video_duration_sec
  } = clip;

  // Confidence score badge
  const rawScore = typeof score === 'number' ? score : 0;
  const normalizedScore = rawScore > 1 ? rawScore : Math.abs(rawScore) * 100;
  const evaluationScore = Math.min(Math.max(0, Math.min(normalizedScore, 100)), 80);
  const confidenceDisplay = `${Math.round(evaluationScore)}% confidence`;

  // Use thumbnail_path if available (presigned URL from backend), otherwise generate from video
  const videoUrl = presigned_url || video_path;
  const { thumbnail, isLoading: thumbnailLoading, error: thumbnailError } = use_thumbnail(
    videoUrl,
    video_id,
    timestamp_start,
    thumbnail_path
  );

  const videoRef = useRef(null);
  const [isHovering, setIsHovering] = useState(false);

  const handleMouseEnter = useCallback(() => {
    if (!videoUrl) return;
    setIsHovering(true);
    const videoEl = videoRef.current;
    if (videoEl) {
      videoEl.volume = 0.5;
      videoEl.currentTime = timestamp_start || 0;
      const playPromise = videoEl.play();
      if (playPromise?.catch) {
        playPromise.catch(() => { });
      }
    }
  }, [timestamp_start, videoUrl]);

  const handleMouseLeave = useCallback(() => {
    const videoEl = videoRef.current;
    if (videoEl) {
      videoEl.pause();
      videoEl.currentTime = timestamp_start || 0;
    }
    setIsHovering(false);
  }, [timestamp_start]);

  const handleTimeUpdate = useCallback(() => {
    const videoEl = videoRef.current;
    if (videoEl && timestamp_end !== undefined) {
      if (videoEl.currentTime >= timestamp_end) {
        videoEl.pause();
        videoEl.currentTime = timestamp_start || 0;
      }
    }
  }, [timestamp_end, timestamp_start]);

  return (
    <div className="bg-gray-100 rounded-2xl px-2 py-4 shadow-sm hover:shadow-md transition-all duration-300">
      {/* Header with number badge and title */}
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-shrink-0 w-8 h-8 bg-white border-2 border-gray-300 rounded-lg flex items-center justify-center">
          <span className="text-sm font-semibold text-gray-700">{index + 1}</span>
        </div>
        <div className="flex-1 min-w-0 flex items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-gray-900 line-clamp-1 leading-tight flex-1">
            {video_name || clip_text || 'Untitled Video'}
          </h3>
          <div className="flex-shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 bg-white rounded-md border border-gray-200">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
            <span className="text-xs font-medium text-gray-600 whitespace-nowrap">
              {formatTimestamp(timestamp_start)} - {formatTimestamp(timestamp_end)}
            </span>
          </div>
        </div>
      </div>

      {/* Video Preview Container */}
      <div
        className="relative w-full aspect-video bg-black rounded-2xl overflow-hidden mb-3 group"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Loading state */}
        {thumbnailLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <Loader2 size={48} className="text-gray-400 animate-spin" />
          </div>
        )}

        {/* Error state */}
        {thumbnailError && !thumbnail && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-gray-400 text-sm">
              Could not load thumbnails
            </div>
          </div>
        )}

        {/* Actual thumbnail */}
        {thumbnail && (
          <img
            src={thumbnail}
            alt={`Thumbnail at ${formatTimestamp(timestamp_start)}`}
            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${isHovering ? 'opacity-0' : 'opacity-100'}`}
            loading="lazy"
          />
        )}

        {/* Hover video preview */}
        {videoUrl && (
          <video
            ref={videoRef}
            src={videoUrl}
            playsInline
            preload="none"
            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-200 ${isHovering ? 'opacity-100' : 'opacity-0'}`}
            onTimeUpdate={handleTimeUpdate}
          />
        )}



      </div>

      {/* Thumbnail strip placeholder */}
      {/* <div className="bg-gray-200 rounded-lg h-16 mb-3 flex items-center justify-center">
        <span className="text-sm text-gray-500">Could not load thumbnails</span>
      </div> */}

      {/* Footer Actions */}
      <div className="flex items-center justify-between mt-4">
        {/* Confidence score badge */}
        <div className="text-sm font-medium text-gray-500">
          {confidenceDisplay}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClick(clip);
          }}
          className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-blue-600 transition-colors"
        >
          <span>View Video</span>
          <Play size={16} />
        </button>
      </div>
    </div>
  );
};

export default VideoClipCardMarengo3;
