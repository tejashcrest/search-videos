# Video Search Frontend

A modern, sleek React application for searching video clips using AI-powered embeddings. Built with React, Vite, TailwindCSS, and Lucide icons.

## Features

- 📤 **Video Upload** - Direct upload to AWS S3 with progress tracking
- 🔄 **Auto-Processing** - Automatic video processing and indexing
- 🔍 **Natural Language Search** - Search videos using plain English queries
- 🎬 **Video Clip Preview** - View matched clips with precise timestamps
- 🖼️ **Smart Thumbnails** - Automatic thumbnail generation from video frames at exact timestamps
- ⚡ **Fast & Responsive** - Built with Vite for lightning-fast performance
- 🎨 **Modern UI** - Sleek design with smooth animations and transitions
- 📱 **Responsive Design** - Works seamlessly on desktop, tablet, and mobile
- 🎯 **Relevance Scoring** - See confidence levels for each match
- 💾 **Intelligent Caching** - Thumbnails cached for optimal performance

## Tech Stack

- **React 18** - Modern React with hooks
- **Vite** - Next-generation frontend tooling
- **TailwindCSS** - Utility-first CSS framework
- **Lucide React** - Beautiful, consistent icons
- **Axios** - HTTP client for API calls
- **AWS SDK** - S3 upload functionality

## Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on `http://localhost:8000`

## Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Update `.env` with your configuration:**
   ```env
   VITE_API_URL=http://localhost:8000
   
   # For video upload feature
   VITE_AWS_ACCESS_KEY_ID=your_access_key
   VITE_AWS_SECRET_ACCESS_KEY=your_secret_key
   VITE_AWS_REGION=us-east-1
   VITE_AWS_BUCKET=jod-testing-anything
   ```
   
   **Note:** See `UPLOAD_SETUP.md` for detailed AWS configuration

## Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Build for Production

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Header.jsx       # App header with navigation
│   │   ├── SearchBar.jsx    # Search input component
│   │   ├── VideoClipCard.jsx # Individual clip card with thumbnails
│   │   ├── VideoPlayer.jsx  # Video player modal
│   │   └── ResultsGrid.jsx  # Grid layout for results
│   ├── hooks/              # Custom React hooks
│   │   └── useThumbnail.js # Thumbnail loading hook
│   ├── services/            # API services
│   │   └── api.js          # Backend API integration
│   ├── utils/              # Utility functions
│   │   ├── formatTime.js   # Time formatting helpers
│   │   └── generateThumbnail.js # Video thumbnail generation
│   ├── App.jsx             # Main app component
│   ├── main.jsx            # App entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── index.html             # HTML template
├── vite.config.js         # Vite configuration
├── tailwind.config.js     # TailwindCSS configuration
├── THUMBNAILS.md          # Thumbnail feature documentation
└── package.json           # Dependencies
```

## API Integration

The frontend connects to the following backend endpoints:

- `POST /search-clips` - Search for video clips
- `POST /process-video` - Process new videos
- `GET /video-status/{video_id}` - Check processing status
- `POST /ask` - Ask questions about videos

## Features in Detail

### Search Interface
- Clean, modern search bar with real-time feedback
- Loading states and error handling
- Clear button for quick query reset

### Video Clip Cards
- **Smart Thumbnails**: Automatically extracted from video at exact timestamp
- **Caching**: Thumbnails cached in sessionStorage for performance
- **Fallback**: Gradient placeholder while loading or on error
- Confidence level badges (HIGH/MEDIUM/LOW)
- Timestamp display and duration
- Relevance score percentage
- Smooth hover animations
- Lazy loading for optimal performance

### Video Player
- Modal overlay with video playback
- Automatic timestamp navigation
- Clip information display
- External link to full video

### Responsive Design
- Mobile-first approach
- Adaptive grid layout (1/2/3 columns)
- Touch-friendly interactions

## Customization

### Colors
Edit `tailwind.config.js` to customize the color scheme:

```js
theme: {
  extend: {
    colors: {
      primary: {
        // Your custom colors
      }
    }
  }
}
```

### API URL
Update the API base URL in `.env`:

```env
VITE_API_URL=https://your-api-domain.com
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance

- Lazy loading for images
- Optimized bundle size
- CSS animations using GPU acceleration
- Efficient re-renders with React hooks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Support

For issues or questions, please open an issue on the GitHub repository.
