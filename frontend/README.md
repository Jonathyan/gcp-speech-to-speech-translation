# Frontend - GCP Speech Translation

Web interface for the live speech-to-speech translation service.

## Quick Start

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Development mode:**
```bash
npm run serve
```
Open http://localhost:3000

3. **Production build:**
```bash
npm run build
npm run serve:prod
```

## Project Structure

```
frontend/
├── public/           # Static files
│   ├── index.html    # Main HTML file
│   └── *.html        # Test pages
├── src/              # Source modules
│   ├── config.js     # Configuration management
│   ├── connection.js # WebSocket handling
│   ├── ui.js         # DOM manipulation
│   ├── utils.js      # Utility functions
│   └── app.js        # Main entry point
├── tests/            # Test files
├── dist/             # Production build output
└── build.js          # Build script
```

## Development Workflow

### 1. Local Development
- Edit files in `src/` directory
- Use `npm run serve` for live development
- Backend: `poetry run uvicorn gcp_speech_to_speech_translation.main:app --reload`

### 2. Testing
```bash
# Run all tests
npm test

# Manual testing
open public/browser-test.html
open public/test-connection.html
```

### 3. Production Build
```bash
# Build optimized version
npm run build

# Test production build
npm run serve:prod
```

## Configuration

### Environment Settings
- **Development:** `ws://localhost:8000/ws`
- **Production:** `wss://your-domain.com/ws`

Update `src/config.js` for custom settings.

### Browser Support
- Modern browsers with WebSocket support
- Chrome 16+, Firefox 11+, Safari 7+, Edge 12+
- Automatic compatibility warnings for unsupported browsers

## Testing Procedures

### Automated Tests
- **Unit tests:** UI components, utilities
- **Integration tests:** E2E user flows
- **Browser tests:** Compatibility checks

### Manual Testing
1. Follow `manual-test-script.md`
2. Test connection scenarios
3. Verify error handling
4. Check responsive design

## Deployment

### Firebase Hosting (Recommended)
```bash
npm run build
firebase deploy --only hosting
```

### Static File Server
```bash
npm run build
# Serve dist/ directory with any static file server
```

## Troubleshooting

### Common Issues
- **WebSocket connection failed:** Check backend server is running
- **CORS errors:** Configure backend to allow frontend origin
- **Build errors:** Ensure all source files exist
- **Test failures:** Check Jest configuration

### Debug Mode
Open browser console for detailed logging:
- Connection attempts
- Error messages
- Environment detection

## Architecture

### Modular Design
- **config.js:** Environment and settings management
- **connection.js:** WebSocket connection handling
- **ui.js:** DOM manipulation and user interactions
- **utils.js:** Browser compatibility and helpers
- **app.js:** Application initialization

### Key Features
- Environment-specific configuration
- Automatic connection retry with exponential backoff
- Browser compatibility detection
- Responsive design
- Comprehensive error handling
- Production-ready build process