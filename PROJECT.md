# Collector Webapp

A Flask-based web application that displays and manages videos collected by a camera-collector Kubernetes pod. The application fetches videos from Google Cloud Storage (GCS), processes them with FFmpeg overlays, and serves them through a web interface.

## Overview

This project serves time-lapse camera footage from Seacliff Beach. Key capabilities:

- Display daily videos collected from the camera
- Add text overlays (timestamps and watermarks) to video content
- Cache processed videos in GCS to reduce processing overhead
- Provide multiple viewing modes (latest, today's videos, monthly compilations)
- RESTful API for video metadata retrieval

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Browser                                 │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Kubernetes LoadBalancer                           │
│                         (port 80)                                    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Flask App (2 replicas)                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Gunicorn WSGI Server                      │    │
│  │                  (2 workers, 120s timeout)                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│        ┌─────────────────────┼─────────────────────┐                │
│        ▼                     ▼                     ▼                │
│  ┌───────────┐        ┌───────────┐        ┌───────────┐           │
│  │  Routes   │        │  FFmpeg   │        │    GCS    │           │
│  │ (app.py)  │───────▶│ Processing│───────▶│  Client   │           │
│  └───────────┘        └───────────┘        └───────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌─────────────────────────────────────┐
                              │     Google Cloud Storage Bucket      │
                              │          (fogcat-webcam)             │
                              │  ┌─────────────┐ ┌─────────────┐    │
                              │  │   Videos    │ │    Cache    │    │
                              │  │ YYYY/MM/*.mp4│ │ cache/*.mp4 │    │
                              │  └─────────────┘ └─────────────┘    │
                              └─────────────────────────────────────┘
```

## Components

### Main Application (app.py)

The Flask application handles all HTTP requests and orchestrates video processing.

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `get_video_list()` | Retrieves videos from GCS for current year/month |
| `send_video(subpath)` | Core video processing - downloads, overlays, caches, serves |
| `latest_blob()` | Returns the most recently updated video blob name |

### Video Processing Pipeline

When a video is requested:

1. Check if a cached version exists in `cache/` directory
2. If cached: download and serve directly
3. If not cached:
   - Download original video from GCS
   - Apply FFmpeg overlays (timestamp + watermark)
   - Upload processed video to cache
   - Serve to client
   - Clean up local temporary files

**FFmpeg Processing Settings:**
- Duration: 15 seconds
- Codec: libx264 with ultrafast preset
- Format: MP4 with faststart flag for web streaming
- Overlays: DejaVu Sans Bold font, size 24, white color

### Frontend

**Templates:**
- `index.html` - Lists today's videos with navigation
- `latest.html` - Dedicated player for the most recent video
- `gallery.html` - Interactive monthly compilations with filtering

**Gallery Features:**
- Filter by year and time of day (sunrise/sunset)
- Dynamic video loading from API
- Modal video player with metadata

### Cache Management

**GCS Lifecycle Policy (lifecycle.yaml):**
- Automatically deletes cached videos older than 1 day
- Applies to all files with `cache/` prefix

**Local Cleanup (expire_video_cache.py):**
- Removes temporary files older than 24 hours from working directory
- Prevents disk space exhaustion

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | HTML page listing today's videos |
| `/health` | GET | Health check - returns `{"status": "ok"}` |
| `/api` | GET | JSON metadata for all videos (URL, timestamp, location) |
| `/video/<path>` | GET | Stream video with FFmpeg overlay and caching |
| `/video_latest` | GET | Stream the most recently updated video |
| `/latest` | GET | HTML page with latest video player |
| `/gallery` | GET | Monthly compilations gallery page |
| `/favicon.ico` | GET | Site favicon |

### API Response Format

The `/api` endpoint returns video metadata extracted from blob names:

```json
[
  {
    "url": "https://example.com/video/2024/01/seacliff-2024-01-15T08:30-01-0800.mp4",
    "datetime": "2024-01-15T08:30",
    "location": "seacliff",
    "segment": "01",
    "timezone": "0800"
  }
]
```

## Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.9 |
| Framework | Flask 2.x with Jinja2 |
| WSGI Server | Gunicorn (2 workers) |
| Video Processing | FFmpeg |
| Cloud Storage | Google Cloud Storage |
| Container | Docker (python:3.9-slim-bullseye) |
| Orchestration | Kubernetes |
| CI/CD | GitHub Actions |

**Python Dependencies:**
- Flask, Flask-CORS
- google-cloud-storage
- gunicorn
- pytz, astral

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BUCKET_NAME` | `fogcat-webcam` | GCS bucket containing videos |
| `VIDEO_WORKING_DIR` | `/app/video` | Local directory for temporary processing |
| `COLLECTOR_API_URL` | (empty) | External API base URL for gallery |
| `GOOGLE_APPLICATION_CREDENTIALS` | `/app/service-account-key.json` | GCP service account key path |
| `TZ` | `America/Los_Angeles` | Application timezone |
| `FLASK_ENV` | `production` | Flask environment |

### GCS Bucket Structure

```
fogcat-webcam/
├── 2024/
│   ├── 01/
│   │   ├── seacliff-2024-01-15T08:30-01-0800.mp4
│   │   └── ...
│   └── 02/
│       └── ...
└── cache/
    └── 2024/01/seacliff-2024-01-15T08:30-01-0800.mp4
```

## Deployment

### Kubernetes Resources

**Deployment (deployment.yaml):**
- 2 replicas for high availability
- GCP credentials mounted from secret
- Container port 5000

**Service (service.yaml):**
- LoadBalancer type
- External port 80 → container port 5000

### CI/CD Pipeline

Triggered on push to `master` branch:

1. Build Docker image with Buildx
2. Push to Docker Hub with `latest` and SHA tags
3. Authenticate to GCP
4. Fetch GKE cluster credentials
5. Deploy new image with `kubectl set image`
6. Verify rollout status

### Manual Deployment

```bash
# Build image
make docker

# Run locally with service account
make run

# Interactive shell for debugging
make shell
```

## Development

### Local Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
```

The development server runs on `http://localhost:5000`.

### Running Tests

```bash
python -m pytest app_test.py -v
```

Tests use mocks for GCS client and subprocess calls.

## File Reference

| File | Description |
|------|-------------|
| `app.py` | Main Flask application |
| `app_test.py` | Unit tests |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container image definition |
| `endpoint.sh` | Container startup script |
| `deployment.yaml` | Kubernetes Deployment |
| `service.yaml` | Kubernetes Service |
| `lifecycle.yaml` | GCS lifecycle policy |
| `expire_video_cache.py` | Local file cleanup utility |
| `Makefile` | Build and run commands |
| `templates/` | Jinja2 HTML templates |
| `static/` | CSS, JS, and favicon |
