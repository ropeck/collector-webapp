#!/usr/local/bin/python

from datetime import datetime
from flask import Flask, render_template, Response, send_from_directory, jsonify
from flask_cors import CORS
from google.cloud import storage
from pytz import timezone
from typing import List
import logging
import os
import re
import subprocess
import traceback


app = Flask(__name__)
CORS(app)  # This enables CORS for all routes

storage_client: storage.Client = storage.Client()
BUCKET_NAME: str = os.environ.get('BUCKET_NAME', "fogcat-webcam")
VIDEO_WORKING_DIR = os.environ.get('VIDEO_WORKING_DIR', "/app/video")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


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


@app.route('/api')
def api() -> str:
    res = []
    for video in get_video_list():
        # Extract components
        match = re.search(r'(\d{4})/(\d{2})/(.*)-(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})-(\d{2})-(\d{4})\.mp4', video.id)

        if match:
            year, month, location, date_time_part, seg_part, timezone_part = match.groups()

            # Construct timestamp string without the unknown `-XX`
            timestamp_str = f"{date_time_part}-{timezone_part}"

            try:
                print(video.id)
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M%z")
                timestamp_iso = dt.astimezone(timezone('UTC')).isoformat(timespec='seconds').replace('+00:00', 'Z')
            except ValueError as e:
                print(f"Timestamp parsing failed for {timestamp_str}: {e}")
                continue  # Skip this entry if parsing fails

            # Correctly formatted URL preserving original structure
            video_url = f"https://weather.fogcat5.com/collector/video/{year}/{month}/seacliff-{date_time_part}-{seg_part}-{timezone_part}.mp4"

            res.append({
                'id': video.id,
                'timestamp': timestamp_iso,
                'url': video_url,
                'location': location,
            })
    res.reverse()

    return jsonify(res), 200


@app.route('/video/<path:subpath>')
def video(subpath: str) -> Response:
    return send_video(subpath)


def get_video_list() -> List[storage.Blob]:
    # Access the GCS bucket with collected videos
    # Example: "2025/01/seacliff"
    prefix = datetime.now().strftime("%Y/%m/seacliff")
    blobs = storage_client.list_blobs(BUCKET_NAME, prefix=prefix)
    if not blobs:
        raise ValueError("No videos found in the bucket.")
    return blobs


def send_video(subpath) -> Response:
    """
    Checks GCS for a cached processed video.
    If not present, downloads the blob, processes it with FFmpeg, uploads the processed file to GCS,
    and serves the video content back.
    """
    blob = storage_client.bucket(BUCKET_NAME).get_blob(subpath)

    if not blob:
        error_message = f"Error: {subpath} does not exist"
        logging.error(error_message)
        return Response(error_message, status=404)

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
        pst = timezone('America/Los_Angeles')
        creation_time_formatted = blob.time_created.astimezone(pst).strftime("%b %-d, %Y %-I:%M %p %Z")
        title_text = creation_time_formatted.replace(":", "\\:")
        watermark_text = "fogcat5"

        # Use FFmpeg to process the video and save to a file
        args = [
            "ffmpeg",
            "-i", local_path,  # Input file
            "-vf",
            f"drawtext=text='{title_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=24:fontcolor=white:x=10:y=10," \
            f"drawtext=text='{watermark_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=24:fontcolor=white:x=w-tw-10:y=10",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-y", processed_path
        ]
        logging.info(f"executing {' '.join(args)}")
        subprocess.run(
            args,
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
        return send_video(latest_blob())
    except ValueError as e:
        logging.error(f"Error fetching latest video: {e}")
        return Response(f"Error: {str(e)}", status=404)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return Response(f"Error: {str(e)}", status=500)


def latest_blob() -> str:
    blobs = get_video_list()
    if not blobs:
        raise ValueError("No blobs found in the bucket.")
    latest = max(blobs, key=lambda b: b.updated)
    logging.info(f"Latest blob: {latest.name}, size: {latest.size}, created at: {latest.time_created}")
    return latest.name


@app.route('/latest')
def latest() -> str:
    return render_template("latest.html",
                           video_url="video_latest",
                           latest_blob=latest_blob())


if __name__ == '__main__':
    app.run(debug=True)
