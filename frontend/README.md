# 청암 챗봇 Frontend

Modern web interface for the 청암 챗봇 RAG system built with vanilla JavaScript and Tailwind CSS.

## Features

- **Document Management**: Upload, view, and delete documents
- **Real-time Chat**: AI-powered chat interface with document context
- **Admin Dashboard**: Comprehensive document and system management
- **Responsive Design**: Works seamlessly on desktop and mobile
- **Korean Language Support**: Full Korean UI and proper Unicode handling

## Tech Stack

- **Vanilla JavaScript** (ES6+)
- **Tailwind CSS** for styling
- **Vite** for development and building
- **No framework dependencies** - lightweight and fast

## Project Structure

```
frontend/
├── public/               # Static HTML files
│   ├── index.html       # Landing page
│   ├── admin.html       # Admin dashboard
│   └── chat.html        # Chat interface
├── src/
│   ├── js/              # JavaScript modules
│   │   ├── admin.js     # Admin dashboard logic
│   │   ├── chat.js      # Chat interface logic
│   │   ├── api.js       # API service layer
│   │   ├── config.js    # Configuration
│   │   ├── utils.js     # Utility functions
│   │   ├── components.js # UI components
│   │   └── logger.js    # Frontend logging
│   └── styles/
│       └── main.css     # Main stylesheet (Tailwind)
├── package.json         # Dependencies
└── vite.config.js       # Vite configuration
```

## Setup

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Development server**
   ```bash
   npm run dev
   ```
   The app will be available at `http://localhost:5173`

3. **Build for production**
   ```bash
   npm run build
   ```
   Built files will be in the `dist/` directory

## Configuration

Update the API endpoint in `/src/js/config.js`:

```javascript
export const API_CONFIG = {
  baseUrl: window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api'
    : window.API_URL || '/api',
};
```

## Key Features

### Document Management
- Drag-and-drop file upload
- Support for PDF, DOC, TXT, PPT, XLS, and more
- Real-time status updates
- Bulk operations (delete multiple)
- Search and filter capabilities

### Chat Interface
- Session management
- Message history
- File context awareness
- Typing indicators
- Error handling

### Admin Dashboard
- Document statistics
- Usage tracking
- System logs viewer
- Responsive data tables
- Export capabilities

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Development

### Code Style
- ES6+ JavaScript
- Modular architecture
- Async/await for API calls
- Proper error handling

### Adding New Features
1. Create new module in `/src/js/`
2. Import in relevant page script
3. Follow existing patterns for consistency

## Deployment

The frontend can be deployed to any static hosting service:

- **Vercel**: `vercel`
- **Netlify**: Drop `dist/` folder
- **GitHub Pages**: Use `dist/` as source
- **AWS S3**: Upload `dist/` contents

## Environment Variables

Set these in your deployment platform:
- `API_URL`: Backend API URL (if not using default)

## License

[Your License Here]