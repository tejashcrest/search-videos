import React, { useState } from 'react';
import { Upload, CheckCircle, XCircle, Loader2, Video, AlertCircle, FileVideo } from 'lucide-react';
import { upload_to_s3, validate_video_file } from '../utils/s3Upload';
import { processVideo, getVideoStatus } from '../services/api';

const VideoUpload = () => {
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, processing, completed, error
  const [s3Url, setS3Url] = useState('');
  const [videoId, setVideoId] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [error, setError] = useState('');
  const [processingStatus, setProcessingStatus] = useState(null);

  // S3 Configuration (should be in environment variables)
  const s3_config = {
    accessKeyId: import.meta.env.VITE_AWS_ACCESS_KEY_ID || '',
    secretAccessKey: import.meta.env.VITE_AWS_SECRET_ACCESS_KEY || '',
    region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
    bucket: import.meta.env.VITE_AWS_BUCKET || 'jod-testing-anything',
  };

  const handle_file_select = (e) => {
    const selected_file = e.target.files[0];
    if (selected_file) {
      const validation = validate_video_file(selected_file);
      if (!validation.valid) {
        setError(validation.error);
        setFile(null);
        return;
      }
      setFile(selected_file);
      setError('');
      setUploadStatus('idle');
    }
  };

  const handle_upload = async () => {
    if (!file) return;

    // Check S3 credentials
    if (!s3_config.accessKeyId || !s3_config.secretAccessKey) {
      setError('AWS credentials not configured. Please set environment variables.');
      return;
    }

    try {
      // Step 1: Upload to S3
      setUploadStatus('uploading');
      setError('');
      
      const url = await upload_to_s3(file, s3_config, (progress) => {
        setUploadProgress(progress);
      });

      setS3Url(url);
      console.log('Video uploaded to S3:', url);

      // Step 2: Process video via backend
      setUploadStatus('processing');
      const response = await processVideo(url);
      setVideoId(response.video_id);

      // Step 3: Poll for processing status
      poll_processing_status(response.video_id);

    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Failed to upload video');
      setUploadStatus('error');
    }
  };

  const poll_processing_status = async (vid_id) => {
    const poll_interval = setInterval(async () => {
      try {
        const status = await getVideoStatus(vid_id);
        setProcessingStatus(status);
        
        if (status.progress) {
          setProcessingProgress(status.progress);
        }

        if (status.status === 'completed') {
          clearInterval(poll_interval);
          setUploadStatus('completed');
        } else if (status.status === 'failed') {
          clearInterval(poll_interval);
          setUploadStatus('error');
          setError(status.error || 'Video processing failed');
        }
      } catch (err) {
        console.error('Status polling error:', err);
      }
    }, 2000); // Poll every 2 seconds

    // Stop polling after 10 minutes
    setTimeout(() => clearInterval(poll_interval), 600000);
  };

  const reset_form = () => {
    setFile(null);
    setUploadProgress(0);
    setUploadStatus('idle');
    setS3Url('');
    setVideoId('');
    setProcessingProgress(0);
    setError('');
    setProcessingStatus(null);
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-600 to-primary-400 rounded-2xl mb-4 shadow-lg">
          <Video size={32} className="text-white" />
        </div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Upload Video</h2>
        <p className="text-gray-600">
          Upload your video to S3 and process it for AI-powered search
        </p>
      </div>

      {/* Upload Card */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
        {uploadStatus === 'idle' || uploadStatus === 'error' ? (
          <>
            {/* File Input */}
            <div className="mb-6">
              <label
                htmlFor="video-upload"
                className="block w-full cursor-pointer"
              >
                <div className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-primary-500 hover:bg-primary-50 transition-all duration-200">
                  <FileVideo size={48} className="mx-auto text-gray-400 mb-4" />
                  <p className="text-lg font-medium text-gray-700 mb-2">
                    {file ? file.name : 'Click to select video'}
                  </p>
                  <p className="text-sm text-gray-500">
                    MP4, WebM, OGG, or MOV (max 500MB)
                  </p>
                </div>
                <input
                  id="video-upload"
                  type="file"
                  accept="video/*"
                  onChange={handle_file_select}
                  className="hidden"
                />
              </label>
            </div>

            {/* File Info */}
            {file && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                  <CheckCircle className="text-green-500" size={24} />
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
                <div>
                  <p className="text-red-700 font-medium">Error</p>
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              </div>
            )}

            {/* Upload Button */}
            <button
              onClick={handle_upload}
              disabled={!file}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload size={20} />
              Upload & Process Video
            </button>
          </>
        ) : (
          <>
            {/* Upload Progress */}
            {uploadStatus === 'uploading' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-700 font-medium">Uploading to S3...</span>
                  <span className="text-primary-600 font-semibold">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-primary-600 to-primary-400 h-full transition-all duration-300 rounded-full"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-sm text-gray-500 text-center">
                  Please wait while we upload your video...
                </p>
              </div>
            )}

            {/* Processing Progress */}
            {uploadStatus === 'processing' && (
              <div className="space-y-4">
                <div className="flex items-center justify-center mb-4">
                  <Loader2 size={48} className="text-primary-600 animate-spin" />
                </div>
                <div className="text-center">
                  <p className="text-lg font-medium text-gray-900 mb-2">
                    Processing Video
                  </p>
                  <p className="text-gray-600 mb-4">
                    Generating embeddings with TwelveLabs...
                  </p>
                  {processingProgress > 0 && (
                    <>
                      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden mb-2">
                        <div
                          className="bg-gradient-to-r from-green-600 to-green-400 h-full transition-all duration-300 rounded-full"
                          style={{ width: `${processingProgress}%` }}
                        />
                      </div>
                      <p className="text-sm text-gray-500">{processingProgress}% complete</p>
                    </>
                  )}
                </div>
                {processingStatus && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">
                      <strong>Status:</strong> {processingStatus.status}
                    </p>
                    {processingStatus.clips_indexed && (
                      <p className="text-sm text-gray-600">
                        <strong>Clips Indexed:</strong> {processingStatus.clips_indexed}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Completion */}
            {uploadStatus === 'completed' && (
              <div className="text-center space-y-4">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-4">
                  <CheckCircle size={48} className="text-green-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900">
                  Video Processed Successfully!
                </h3>
                <p className="text-gray-600">
                  Your video has been uploaded and indexed. You can now search for clips.
                </p>
                {processingStatus?.clips_indexed && (
                  <div className="inline-block px-4 py-2 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-green-700 font-medium">
                      {processingStatus.clips_indexed} clips indexed
                    </p>
                  </div>
                )}
                <div className="pt-4 space-y-3">
                  <a
                    href="/"
                    className="btn-primary inline-block"
                  >
                    Go to Search
                  </a>
                  <button
                    onClick={reset_form}
                    className="btn-secondary block w-full"
                  >
                    Upload Another Video
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Info Section */}
      <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-xl">
        <h4 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
          <AlertCircle size={20} />
          How it works
        </h4>
        <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
          <li>Video is uploaded to AWS S3 bucket</li>
          <li>TwelveLabs generates embeddings for video segments</li>
          <li>Embeddings are indexed in OpenSearch</li>
          <li>Video becomes searchable using natural language</li>
        </ol>
      </div>
    </div>
  );
};

export default VideoUpload;
