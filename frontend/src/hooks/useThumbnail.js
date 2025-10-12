import { useState, useEffect } from 'react';
import { get_or_generate_thumbnail } from '../utils/thumbnailGenerator';

/**
 * Custom hook to load video thumbnails
 */
export const use_thumbnail = (videoUrl, videoId, timestamp) => {
  const [thumbnail, setThumbnail] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const load_thumbnail = async () => {
      if (!videoUrl || videoId === undefined || timestamp === undefined) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const thumbnailUrl = await get_or_generate_thumbnail(videoUrl, videoId, timestamp);
        
        if (isMounted) {
          setThumbnail(thumbnailUrl);
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err);
          setIsLoading(false);
          console.error('Thumbnail loading error:', err.message);
        }
      }
    };

    load_thumbnail();

    return () => {
      isMounted = false;
    };
  }, [videoUrl, videoId, timestamp]);

  return { thumbnail, isLoading, error };
};
