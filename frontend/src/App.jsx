import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import SearchBar from './components/SearchBar';
import ResultsGrid from './components/ResultsGrid';
import VideoPlayer from './components/VideoPlayer';
import VideoUpload from './components/VideoUpload';
import VideoExplore from './components/VideoExplore';
import { searchClips } from './services/api';
import { AlertCircle, Search } from 'lucide-react';
import { motion } from 'framer-motion';

function App() {
  const [currentPage, setCurrentPage] = useState('explore'); // 'search' or 'upload'
  const [clips, setClips] = useState([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedClip, setSelectedClip] = useState(null);
  const [hasSearched, setHasSearched] = useState(false); // Track if user has searched

  const handle_search = async (searchQuery, searchType) => {
    setIsLoading(true);
    setError(null);
    setQuery(searchQuery);
    setHasSearched(true); // Mark that a search has been performed

    try {
      console.log("Sending req. to API with", searchQuery, searchType)
      const response = await searchClips(searchQuery, 10, searchType);
      setClips(response.clips);
      setTotal(response.total);
    } catch (err) {
      setError('Failed to search videos. Please try again.');
      console.error('Search error:', err);
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      {/* Sidebar */}
      <Sidebar activeTab={currentPage} setActiveTab={setCurrentPage} />

      {/* Main Content - with left margin for fixed sidebar */}
      <main className="ml-20 flex flex-col items-center px-8 py-12 min-h-screen">
        {currentPage === 'upload' ? (
          <VideoUpload />
        ) : currentPage === 'explore' ? (
          <VideoExplore />
        ) : (
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
                  <h1 className="text-5xl font-extrabold bg-gradient-to-r from-blue-600 to-blue-400 bg-clip-text text-transparent mb-3">
                    Where should we begin?
                  </h1>
                  <p className="text-blue-600 text-lg">
                    Search your video library with natural language
                  </p>
                </motion.div>
              )}

              {/* Search Bar - Animates from center to top */}
              <motion.div
                layout
                transition={{ duration: 0.5, ease: 'easeInOut' }}
                className="w-full max-w-2xl mb-6"
              >
                <SearchBar onSearch={handle_search} isLoading={isLoading} />
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
                    onClick={() => handle_search('person walking in park')}
                    className="px-4 py-2 bg-white border border-blue-200 rounded-full hover:border-blue-600 hover:bg-blue-50 transition-all text-sm text-gray-700"
                  >
                    person walking in park
                  </button>
                  <button
                    onClick={() => handle_search('sunset scene')}
                    className="px-4 py-2 bg-white border border-blue-200 rounded-full hover:border-blue-600 hover:bg-blue-50 transition-all text-sm text-gray-700"
                  >
                    sunset scene
                  </button>
                  <button
                    onClick={() => handle_search('people talking')}
                    className="px-4 py-2 bg-white border border-blue-200 rounded-full hover:border-blue-600 hover:bg-blue-50 transition-all text-sm text-gray-700"
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
                    <div className="inline-block w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
                    <p className="text-gray-600">Searching videos...</p>
                  </div>
                )}

                {/* Results */}
                {!isLoading && clips.length > 0 && (
                  <div className="w-full max-w-6xl mx-auto">
                    <ResultsGrid
                      clips={clips}
                      total={total}
                      query={query}
                      onClipClick={handle_clip_click}
                    />
                  </div>
                )}

                {/* No Results */}
                {!isLoading && query && clips.length === 0 && (
                  <div className="text-center py-16">
                    <div className="w-24 h-24 bg-gradient-to-br from-blue-100 to-blue-200 rounded-full flex items-center justify-center mx-auto mb-6">
                      <Search size={48} className="text-blue-600" />
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
          </div>
        )}
      </main>

      {/* Video Player Modal */}
      {selectedClip && (
        <VideoPlayer clip={selectedClip} onClose={close_player} />
      )}
    </div>
  );
}

export default App;
