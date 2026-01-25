# Changelog

All notable changes to the Collector Webapp project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.3.0] - 2026-01-24

### Added
- Dedicated sunset collections gallery at `/sunset-gallery`
- New sunset-themed UI with purple/orange gradient design
- Sunset gallery features:
  - Browse months with sunset videos
  - Filter by year
  - Click to play sunset compilations in modal
  - Shows video count, duration, and file size metadata
- New static assets: `static/sunset/app.js` and `static/sunset/style.css`
- Navigation link to sunset gallery in all templates
- 4 new tests for sunset gallery route
- PROJECT.md with comprehensive architecture documentation
- INTEGRATION_PLAN.md documenting the sunset collections integration

## [0.2.0] - 2026-01-24

### Added
- Monthly compilations gallery at `/gallery`
- Gallery features:
  - Grid view of available months with thumbnails
  - Year and time-of-day (sunrise/sunset) filtering
  - On-demand compilation generation
  - Video player with metadata display
- Gallery static assets in `static/gallery/`
- Navigation links between index, latest, and gallery pages
- `COLLECTOR_API_URL` environment variable for API integration

## [0.1.0] - 2025-01-24

### Added
- Initial Flask web application
- Video display with FFmpeg text overlays (timestamp and watermark)
- GCS caching for processed videos
- Endpoints:
  - `/` - List today's videos
  - `/health` - Health check
  - `/api` - JSON video metadata
  - `/video/<path>` - Stream video with overlay
  - `/video_latest` - Stream most recent video
  - `/latest` - Latest video player page
- Docker containerization with Gunicorn
- Kubernetes deployment configuration
- GitHub Actions CI/CD pipeline
- Comprehensive test suite

[Unreleased]: https://github.com/ropeck/collector-webapp/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ropeck/collector-webapp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ropeck/collector-webapp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ropeck/collector-webapp/releases/tag/v0.1.0
