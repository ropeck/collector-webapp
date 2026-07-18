# camera_collector_webapp

This is a Flask web application for displaying videos collected by the camera-collector system.

## Development Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   python app.py
   ```

## Deployment

Runs on **Cloud Run** (as of 2026-07-18), not GKE — see
[PROJECT.md](PROJECT.md#deployment) for the current setup, including why it's
fully public rather than IAP-gated. The old push-to-GKE CI/CD pipeline is
retired.