# Integrated Sunset Collections App

A plan for an integrated application that combines camera-collector and collector-webapp to display sunset monthly compilations.

## Goal

Create a unified experience for browsing and viewing sunset time-lapse compilations organized by month, leveraging both existing services.

## Current State

### camera-collector
- Captures daily sunrise/sunset videos from YouTube stream
- Generates monthly compilations via `/api/compilation/generate`
- Stores videos in GCS: `YYYY/MM/compilations/sunset-YYYY-MM.mp4`
- API returns compilation URL, duration, file size

### collector-webapp
- Displays individual daily videos with FFmpeg overlays
- Has gallery page for monthly compilations
- Fetches data from `COLLECTOR_API_URL` environment variable

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Browser                                 │
│                    Sunset Collections Gallery                        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      collector-webapp                                │
│                     (Flask Frontend)                                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  /sunset-gallery                                             │    │
│  │  - Lists all available months                                │    │
│  │  - Displays compilation thumbnails                           │    │
│  │  - Video player with metadata                                │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      camera-collector                                │
│                      (FastAPI Backend)                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  /api/months                    - List available months      │    │
│  │  /api/compilation/generate      - Generate/retrieve video    │    │
│  │  /api/compilation/{year}/{month}?time_filter=sunset          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Google Cloud Storage                              │
│              fogcat-webcam/YYYY/MM/compilations/                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Backend API Enhancements (camera-collector)

**1.1 Add sunset-specific endpoint**
```
GET /api/sunset/months
```
Returns list of months with sunset compilation status:
```json
[
  {
    "year": 2024,
    "month": 1,
    "video_count": 28,
    "compilation_exists": true,
    "compilation_url": "https://storage.googleapis.com/...",
    "duration_seconds": 420,
    "thumbnail_url": "https://storage.googleapis.com/..."
  }
]
```

**1.2 Add thumbnail generation**
- Extract frame from compilation at 50% duration
- Store as `YYYY/MM/compilations/sunset-YYYY-MM-thumb.jpg`
- Return thumbnail URL in API responses

**1.3 Add compilation metadata endpoint**
```
GET /api/sunset/compilation/{year}/{month}
```
Returns detailed metadata for a specific compilation.

### Phase 2: Frontend Gallery (collector-webapp)

**2.1 New route and template**
- Add `/sunset-gallery` route in app.py
- Create `templates/sunset_gallery.html`

**2.2 Gallery features**
- Grid of month cards with thumbnails
- Year filter dropdown
- Click to play compilation in modal
- Show metadata: duration, video count, date range

**2.3 Template structure**
```html
<!-- sunset_gallery.html -->
<div class="sunset-gallery">
  <header>
    <h1>Seacliff Beach Sunset Collections</h1>
    <select id="year-filter">...</select>
  </header>

  <div class="month-grid">
    <!-- Month cards with thumbnails -->
  </div>

  <div class="video-modal">
    <!-- Video player overlay -->
  </div>
</div>
```

**2.4 JavaScript functionality**
- Fetch months from camera-collector API
- Lazy-load thumbnails
- On-demand compilation generation with loading indicator
- Video player controls

### Phase 3: Integration

**3.1 Service communication**
- collector-webapp calls camera-collector via `COLLECTOR_API_URL`
- Add CORS headers if needed (already has Flask-CORS)
- Handle API errors gracefully with user feedback

**3.2 Kubernetes networking**
- Services communicate via ClusterIP
- Set `COLLECTOR_API_URL=http://camera-collector-service`

**3.3 Caching strategy**
- Compilations cached in GCS (already implemented)
- Frontend caches month list for session
- Thumbnails served directly from GCS

### Phase 4: Polish

**4.1 UI enhancements**
- Responsive grid layout for mobile
- Smooth transitions and loading states
- Error handling with retry options

**4.2 Navigation**
- Add link from main gallery to sunset gallery
- Breadcrumb navigation
- Deep linking to specific months (`/sunset-gallery?month=2024-06`)

**4.3 Performance**
- Lazy load off-screen thumbnails
- Preload next/prev month compilations
- Progress indicator for long compilations

## API Contract

### camera-collector endpoints used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/months` | GET | List all months with video counts |
| `/api/compilation/generate` | POST | Generate sunset compilation |
| `/api/compilation/{year}/{month}?time_filter=sunset` | GET | Get compilation status |

### Request/Response Examples

**List months:**
```bash
GET /api/months

Response:
{
  "months": [
    {"year": 2024, "month": 12, "count": 45},
    {"year": 2024, "month": 11, "count": 58}
  ]
}
```

**Generate compilation:**
```bash
POST /api/compilation/generate
Content-Type: application/json

{
  "year": 2024,
  "month": 6,
  "time_filter": "sunset"
}

Response:
{
  "url": "https://storage.googleapis.com/fogcat-webcam/2024/06/compilations/sunset-2024-06.mp4",
  "duration": 420.5,
  "size_mb": 85.2,
  "video_count": 28
}
```

## File Changes

### camera-collector
| File | Changes |
|------|---------|
| `app.py` | Add `/api/sunset/months` endpoint |
| `concat.py` | Add thumbnail generation function |

### collector-webapp
| File | Changes |
|------|---------|
| `app.py` | Add `/sunset-gallery` route |
| `templates/sunset_gallery.html` | New gallery template |
| `static/sunset/app.js` | Gallery JavaScript |
| `static/sunset/style.css` | Gallery styles |

## Timeline

| Phase | Description |
|-------|-------------|
| Phase 1 | Backend API enhancements |
| Phase 2 | Frontend gallery implementation |
| Phase 3 | Service integration and testing |
| Phase 4 | Polish and optimization |

## Dependencies

- camera-collector API must be accessible from collector-webapp
- GCS bucket must allow public read for compilation videos
- Both services deployed to same Kubernetes cluster

## Success Criteria

- [ ] User can browse all available months with sunset compilations
- [ ] Thumbnails load for each month
- [ ] Clicking a month plays the compilation video
- [ ] Compilations generate on-demand if not cached
- [ ] Loading states shown during generation
- [ ] Works on mobile devices
