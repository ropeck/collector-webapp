#!/usr/local/bin/python

from datetime import datetime
from flask import Flask, render_template, Response, send_from_directory, jsonify
from google.cloud import storage
from typing import List
import logging
import os
import subprocess
import traceback

app = Flask(__name__)
storage_client: storage.Client = storage.Client()
BUCKET_NAME: str = os.environ.get('BUCKET_NAME', "fogcat-webcam")
VIDEO_WORKING_DIR = os.environ.get('VIDEO_WORKING_DIR', "/app/video")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


# icon for browser tabs
@app.route('/favicon.ico')
def favicon() -> Response:
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route('/')
def index() -> str:
    # Replace with actual GCS logic
    videos = get_video_list()
    return render_template('index.html', videos=videos)


@app.route('/video/<path:subpath>')
def video(subpath: str) -> Response:
    blob = storage_client.bucket(BUCKET_NAME).get_blob(subpath)
    return send_video(blob)


def get_video_list() -> List[storage.Blob]:
    # Access the GCS bucket with collected videos
    # Example: "2025/01/seacliff"
    prefix = datetime.now().strftime("%Y/%m/seacliff")
    blobs = storage_client.list_blobs(BUCKET_NAME, prefix=prefix)
    if not blobs:
        raise ValueError("No videos found in the bucket.")
    return blobs

def send_video(blob: storage.Blob) -> Response:
    """
    Checks GCS for a cached processed video.
    If not present, downloads the blob, processes it with FFmpeg, uploads the processed file to GCS,
    and serves the video content back.
    """
    # Define GCS paths
    gcs_cache_path = f"cache/{blob.name.replace('/', '_')}.mp4"
    logging.info(f"cache path {gcs_cache_path}")

    # Initialize GCS client and bucket
    bucket = storage_client.bucket(BUCKET_NAME)
    cached_blob = bucket.blob(gcs_cache_path)

    # Local paths for temporary processing
    basename = f"{blob.name.replace('/', '_')}.mp4"
    if not os.path.exists(VIDEO_WORKING_DIR):
        os.makedirs(VIDEO_WORKING_DIR)
    local_path = os.path.join(VIDEO_WORKING_DIR, basename)
    processed_path = os.path.join(VIDEO_WORKING_DIR, f"processed_{basename}")


    try:
        # Check if the processed video is already in GCS
        if cached_blob.exists():
            # Serve the cached processed video from GCS
            logging.info(f"Serving cached video from GCS: {gcs_cache_path}")
            processed_video_content = cached_blob.download_as_bytes()
            return Response(processed_video_content, content_type="video/mp4")

        # not in cache, create the overlayed video and upload to cache
        # Download blob to local file
        blob.download_to_filename(local_path)

        # Properly format the text arguments
        from pytz import timezone
        pst = timezone('America/Los_Angeles')
        creation_time_formatted = blob.time_created.astimezone(pst).strftime("%b %-d, %Y %-I:%M %p %Z")
        title_text = creation_time_formatted.replace(":", "\\:")
        watermark_text = "fogcat5"

        # Use FFmpeg to process the video and save to a file
        subprocess.run(
            [
                "ffmpeg",
                "-i", local_path,  # Input file
                "-vf",
                f"drawtext=text='{title_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=24:fontcolor=white:x=10:y=10," \
                f"drawtext=text='{watermark_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=24:fontcolor=white:x=w-tw-10:y=10",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-movflags", "+faststart",
                "-y", processed_path
            ],
            check=True
        )

        # Upload the processed file to GCS
        cached_blob.upload_from_filename(processed_path)
        logging.info(f"Uploaded processed video to GCS: {gcs_cache_path}")

        # Serve the processed video file
        with open(processed_path, "rb") as video_file:
            return Response(video_file.read(), content_type="video/mp4")

    except Exception as e:
        tb = traceback.format_exc()
        error_message = f"{str(e)}{tb}"
        logging.error(f"Error processing video: {error_message}")
        return Response(f"Error: {error_message}", status=500)
    finally:
        # Cleanup local files
        if os.path.exists(local_path):
            os.remove(local_path)
        if os.path.exists(processed_path):
            os.remove(processed_path)


@app.route('/video_latest')
def video_latest() -> Response:
    try:
        blob = latest_blob()
        return send_video(blob)
    except ValueError as e:
        logging.error(f"Error fetching latest video: {e}")
        return Response(f"Error: {str(e)}", status=404)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return Response(f"Error: {str(e)}", status=500)


def latest_blob() -> storage.Blob:
    blobs = get_video_list()
    if not blobs:
        raise ValueError("No blobs found in the bucket.")
    latest = max(blobs, key=lambda b: b.updated)
    logging.info(f"Latest blob: {latest.name}, size: {latest.size}, created at: {latest.time_created}")
    return latest


@app.route('/latest')
def latest() -> str:
    return render_template("latest.html",
                           video_url="video_latest",
                           latest_blob=str(latest_blob()))


if __name__ == '__main__':
    app.run(debug=True)
