import React, { useState } from 'react';
import SearchBarMarengo3 from './SearchBarMarengo3';
import ResultsGrid from './ResultsGrid';
import VideoPlayer from './VideoPlayer';
import { searchClipsMarengo3 } from '../services/api';
import { AlertCircle, Search } from 'lucide-react';
import { motion } from 'framer-motion';

function SearchMarengo3() {
  const [clips, setClips] = useState([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedClip, setSelectedClip] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handle_search = async (searchQuery, searchType, topK = 20, imageResponse = null, imageFile = null) => {
    setIsLoading(true);
    setError(null);
    setQuery(searchQuery || '');
    setHasSearched(true);

    try {
      // If imageResponse is provided (from image search), use it directly
      if (imageResponse) {
        console.log("Using image search response (Marengo 3)");
        setClips(imageResponse.clips);
        setTotal(imageResponse.total);
      } 
      // Otherwise perform unified search (text, image, or combined)
      else {
        console.log("Performing unified search (Marengo 3):", {
          hasText: !!searchQuery,
          hasImage: !!imageFile,
          topK,
          searchType
        });
        const response = await searchClipsMarengo3(searchQuery, topK, searchType, imageFile);
        setClips(response.clips);
        setTotal(response.total);
      }
    } catch (err) {
      setError('Failed to search videos (Marengo 3). Please try again.');
      console.error('Search error (Marengo 3):', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handle_clip_click = (clip) => {
    setSelectedClip(clip);
  };

  const close_player = () => {
    setSelectedClip(null);
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* Centered Search (Initial State) or Top Search (After Search) */}
      <motion.div
        layout
        initial={false}
        animate={{
          justifyContent: hasSearched ? 'flex-start' : 'center',
          paddingTop: hasSearched ? '2rem' : '0',
        }}
        transition={{ duration: 0.5, ease: 'easeInOut' }}
        className="flex flex-col items-center w-full"
        style={{ minHeight: hasSearched ? 'auto' : '80vh' }}
      >
        {/* Hero Section - Only show when not searched */}
        {!hasSearched && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-8"
          >
            <div className="flex items-center justify-center gap-2 mb-3">
              <h1 className="text-5xl font-extrabold bg-gradient-to-r from-purple-600 to-purple-400 bg-clip-text text-transparent">
                Marengo 3 Search
              </h1>
              <span className="text-3xl">✨</span>
            </div>
            <p className="text-purple-600 text-lg">
              Next-generation video search with Marengo 3 embeddings
            </p>
          </motion.div>
        )}

        {/* Search Bar - Animates from center to top */}
        <motion.div
          layout
          transition={{ duration: 0.5, ease: 'easeInOut' }}
          className="w-full max-w-2xl mb-6"
        >
          <SearchBarMarengo3
            onSearch={handle_search}
            isLoading={isLoading}
            queryValue={query}
            onQueryChange={setQuery}
          />
        </motion.div>

        {/* Suggestion chips - Only show when not searched */}
        {!hasSearched && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-wrap gap-2 justify-center max-w-2xl"
          >
            <button
              onClick={() => {
                handle_search('person walking in park');
              }}
              className="px-4 py-2 bg-white border border-purple-200 rounded-full hover:border-purple-600 hover:bg-purple-50 transition-all text-sm text-gray-700"
            >
              person walking in park
            </button>
            <button
              onClick={() => {
                handle_search('sunset scene')
              }
            }
              className="px-4 py-2 bg-white border border-purple-200 rounded-full hover:border-purple-600 hover:bg-purple-50 transition-all text-sm text-gray-700"
            >
              sunset scene
            </button>
            <button
              onClick={() => {
                handle_search('people talking')
              }
              }
              className="px-4 py-2 bg-white border border-purple-200 rounded-full hover:border-purple-600 hover:bg-purple-50 transition-all text-sm text-gray-700"
            >
              people talking
            </button>
          </motion.div>
        )}
      </motion.div>

      {/* Results Section - Only show after search */}
      {hasSearched && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="w-full px-8"
        >
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700 max-w-2xl mx-auto">
              <AlertCircle size={20} />
              <span>{error}</span>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-16">
              <div className="inline-block w-16 h-16 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-4"></div>
              <p className="text-gray-600">Searching videos with Marengo 3...</p>
            </div>
          )}

          {/* Results */}
          {!isLoading && clips.length > 0 && (
            <div className="w-full max-w-7xl mx-auto">
              <ResultsGrid
                clips={clips}
                total={total}
                query={query}
                onClipClick={handle_clip_click}
                from={"Marengo 3"}
              />
            </div>
          )}

          {/* No Results */}
          {!isLoading && query && clips.length === 0 && (
            <div className="text-center py-16">
              <div className="w-24 h-24 bg-gradient-to-br from-purple-100 to-purple-200 rounded-full flex items-center justify-center mx-auto mb-6">
                <Search size={48} className="text-purple-600" />
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">
                No results found
              </h3>
              <p className="text-gray-600">
                Try a different search query
              </p>
            </div>
          )}
        </motion.div>
      )}

      {/* Video Player Modal */}
      {selectedClip && (
        <VideoPlayer clip={selectedClip} onClose={close_player} />
      )}
    </div>
  );
}

export default SearchMarengo3;
