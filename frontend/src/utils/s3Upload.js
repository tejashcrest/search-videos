import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { Upload } from '@aws-sdk/lib-storage';

/**
 * Upload a file to S3 with progress tracking
 * @param {File} file - The file to upload
 * @param {Object} config - AWS configuration
 * @param {Function} onProgress - Progress callback (percent)
 * @returns {Promise<string>} - The S3 URL of the uploaded file
 */
export const upload_to_s3 = async (file, config, onProgress) => {
  const { accessKeyId, secretAccessKey, region, bucket } = config;

  // Create S3 client
  const s3Client = new S3Client({
    region: region,
    credentials: {
      accessKeyId: accessKeyId,
      secretAccessKey: secretAccessKey,
    },
  });

  // Generate unique filename
  const timestamp = Date.now();
  const sanitized_name = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
  const key = `videos/${timestamp}_${sanitized_name}`;

  try {
    // For files smaller than 100MB, use simple PutObject (no multipart, no checksum issues)
    const use_simple_upload = file.size < 100 * 1024 * 1024;
    
    // Convert File to ArrayBuffer for compatibility
    const fileBuffer = await file.arrayBuffer();
    
    if (use_simple_upload) {
      // Simple upload for smaller files
      const command = new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: new Uint8Array(fileBuffer),
        ContentType: file.type,
        ACL: 'public-read',
      });

      // Track progress manually for simple upload
      if (onProgress) {
        onProgress(50); // Show 50% while uploading
      }

      await s3Client.send(command);

      if (onProgress) {
        onProgress(100); // Complete
      }
    } else {
      // Multipart upload for larger files
      const upload = new Upload({
        client: s3Client,
        params: {
          Bucket: bucket,
          Key: key,
          Body: new Uint8Array(fileBuffer),
          ContentType: file.type,
          ACL: 'public-read',
        },
        // Upload configuration
        queueSize: 4,
        partSize: 1024 * 1024 * 10, // 10MB per part
        leavePartsOnError: false,
      });

      // Track progress
      upload.on('httpUploadProgress', (progress) => {
        const percent = Math.round((progress.loaded / progress.total) * 100);
        if (onProgress) {
          onProgress(percent);
        }
      });

      // Execute upload
      await upload.done();
    }

    // Return public URL
    const url = `https://${bucket}.s3.${region}.amazonaws.com/${key}`;
    return url;
  } catch (error) {
    console.error('S3 upload error:', error);
    throw new Error(`Failed to upload to S3: ${error.message}`);
  }
};

/**
 * Validate file before upload
 */
export const validate_video_file = (file) => {
  const max_size = 500 * 1024 * 1024; // 500MB
  const allowed_types = ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'];

  if (!file) {
    return { valid: false, error: 'No file selected' };
  }

  if (file.size > max_size) {
    return { valid: false, error: 'File size exceeds 500MB limit' };
  }

  if (!allowed_types.includes(file.type)) {
    return { valid: false, error: 'Invalid file type. Please upload MP4, WebM, OGG, or MOV' };
  }

  return { valid: true };
};
