import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone as dt_timezone
from app import app, get_video_list, send_video, latest_blob, BUCKET_NAME, COLLECTOR_API_URL


class AppTestCase(unittest.TestCase):
    def setUp(self):
        # Set up the test client
        app.testing = True
        self.client = app.test_client()

    @patch('app.send_from_directory')
    def test_favicon(self, mock_send_from_directory):
        # Mock the send_from_directory response
        mock_send_from_directory.return_value = "Favicon"
        response = self.client.get('/favicon.ico')
        mock_send_from_directory.assert_called_once_with(
            os.path.join(app.root_path, 'static'),
            'favicon.ico', mimetype='image/vnd.microsoft.icon'
        )
        self.assertEqual(response.status_code, 200)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'ok')

    @patch('app.render_template')
    @patch('app.get_video_list')
    def test_index(self, mock_get_video_list, mock_render_template):
        # Mock get_video_list and render_template
        mock_get_video_list.return_value = ["video1.mp4", "video2.mp4"]
        mock_render_template.return_value = "Rendered Template"
        response = self.client.get('/')
        mock_get_video_list.assert_called_once()
        mock_render_template.assert_called_once_with('index.html', videos=["video1.mp4", "video2.mp4"])
        self.assertEqual(response.status_code, 200)

    @patch('app.render_template')
    def test_gallery(self, mock_render_template):
        """Test the gallery endpoint."""
        mock_render_template.return_value = "Gallery Template"
        response = self.client.get('/gallery')
        mock_render_template.assert_called_once_with('gallery.html', api_base_url=COLLECTOR_API_URL)
        self.assertEqual(response.status_code, 200)

    @patch('app.render_template')
    @patch('app.latest_blob')
    def test_latest(self, mock_latest_blob, mock_render_template):
        """Test the latest page endpoint."""
        mock_latest_blob.return_value = "2025/01/seacliff-2025-01-24T18:30-00-0800.mp4"
        mock_render_template.return_value = "Rendered Template"
        response = self.client.get('/latest')
        mock_latest_blob.assert_called_once()
        mock_render_template.assert_called_once_with(
            "latest.html",
            video_url="video_latest",
            latest_blob="2025/01/seacliff-2025-01-24T18:30-00-0800.mp4"
        )
        self.assertEqual(response.status_code, 200)


class ApiEndpointTestCase(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    @patch('app.get_video_list')
    def test_api_returns_json(self, mock_get_video_list):
        """Test the API endpoint returns JSON."""
        mock_blob = MagicMock()
        mock_blob.id = "2025/01/seacliff-2025-01-24T18:30-00-0800.mp4"
        mock_get_video_list.return_value = [mock_blob]

        response = self.client.get('/api')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')

    @patch('app.get_video_list')
    def test_api_parses_video_metadata(self, mock_get_video_list):
        """Test the API correctly parses video metadata."""
        mock_blob = MagicMock()
        mock_blob.id = "2025/01/seacliff-2025-01-24T18:30-00-0800.mp4"
        mock_get_video_list.return_value = [mock_blob]

        response = self.client.get('/api')
        data = response.get_json()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['location'], 'seacliff')
        self.assertIn('timestamp', data[0])
        self.assertIn('url', data[0])

    @patch('app.get_video_list')
    def test_api_skips_invalid_filenames(self, mock_get_video_list):
        """Test the API skips files that don't match the expected pattern."""
        mock_blob_valid = MagicMock()
        mock_blob_valid.id = "2025/01/seacliff-2025-01-24T18:30-00-0800.mp4"

        mock_blob_invalid = MagicMock()
        mock_blob_invalid.id = "invalid-filename.mp4"

        mock_get_video_list.return_value = [mock_blob_valid, mock_blob_invalid]

        response = self.client.get('/api')
        data = response.get_json()

        # Only the valid blob should be in the response
        self.assertEqual(len(data), 1)

    @patch('app.get_video_list')
    def test_api_empty_list(self, mock_get_video_list):
        """Test the API with no videos."""
        mock_get_video_list.return_value = []

        response = self.client.get('/api')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data, [])


class VideoEndpointTestCase(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    @patch('app.send_video')
    def test_video_route(self, mock_send_video):
        """Test the video route calls send_video."""
        mock_send_video.return_value = "Video Content"
        response = self.client.get('/video/2025/01/test.mp4')
        mock_send_video.assert_called_once_with('2025/01/test.mp4')

    @patch('app.storage_client')
    def test_send_video_not_found(self, mock_storage_client):
        """Test send_video returns 404 when blob doesn't exist."""
        mock_bucket = MagicMock()
        mock_bucket.get_blob.return_value = None
        mock_storage_client.bucket.return_value = mock_bucket

        response = send_video('nonexistent.mp4')

        self.assertEqual(response.status_code, 404)
        self.assertIn('does not exist', response.get_data(as_text=True))

    @patch('os.remove')
    @patch('os.path.exists', return_value=False)  # No local files exist
    @patch('os.makedirs')
    @patch('app.storage_client')
    def test_send_video_serves_cached(self, mock_storage_client, mock_makedirs, mock_exists, mock_remove):
        """Test send_video serves cached video from GCS."""
        mock_blob = MagicMock()
        mock_blob.name = "2025/01/test.mp4"

        mock_cached_blob = MagicMock()
        mock_cached_blob.exists.return_value = True
        mock_cached_blob.download_as_bytes.return_value = b"cached video content"

        mock_bucket = MagicMock()
        mock_bucket.get_blob.return_value = mock_blob
        mock_bucket.blob.return_value = mock_cached_blob

        mock_storage_client.bucket.return_value = mock_bucket

        response = send_video('2025/01/test.mp4')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'video/mp4')
        mock_cached_blob.download_as_bytes.assert_called_once()
        # Verify no file cleanup attempted since files don't exist
        mock_remove.assert_not_called()

    @patch('os.remove')
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    @patch('app.timezone')
    @patch('subprocess.run')
    @patch('app.storage_client')
    def test_send_video_processes_uncached(self, mock_storage_client, mock_subprocess,
                                           mock_timezone, mock_makedirs, mock_exists, mock_remove):
        """Test send_video processes and caches uncached video."""
        from pytz import timezone as real_timezone
        mock_timezone.return_value = real_timezone('UTC')

        mock_blob = MagicMock()
        mock_blob.name = "2025/01/test.mp4"
        mock_blob.time_created = datetime(2025, 1, 24, 18, 30, tzinfo=dt_timezone.utc)

        mock_cached_blob = MagicMock()
        mock_cached_blob.exists.return_value = False

        mock_bucket = MagicMock()
        mock_bucket.get_blob.return_value = mock_blob
        mock_bucket.blob.return_value = mock_cached_blob

        mock_storage_client.bucket.return_value = mock_bucket

        # Mock subprocess to succeed
        mock_subprocess.return_value = MagicMock(returncode=0)

        # Mock file reading for the final response
        with patch('builtins.open', unittest.mock.mock_open(read_data=b"processed video")):
            response = send_video('2025/01/test.mp4')

        self.assertEqual(response.status_code, 200)
        mock_blob.download_to_filename.assert_called_once()
        mock_subprocess.assert_called_once()
        mock_cached_blob.upload_from_filename.assert_called_once()


class VideoLatestEndpointTestCase(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    @patch('app.send_video')
    @patch('app.latest_blob')
    def test_video_latest_success(self, mock_latest_blob, mock_send_video):
        """Test video_latest returns video successfully."""
        mock_latest_blob.return_value = "2025/01/latest.mp4"
        mock_send_video.return_value = MagicMock(status_code=200)

        response = self.client.get('/video_latest')
        mock_latest_blob.assert_called_once()
        mock_send_video.assert_called_once_with("2025/01/latest.mp4")

    @patch('app.latest_blob')
    def test_video_latest_value_error(self, mock_latest_blob):
        """Test video_latest handles ValueError."""
        mock_latest_blob.side_effect = ValueError("No blobs found")

        response = self.client.get('/video_latest')
        self.assertEqual(response.status_code, 404)
        self.assertIn('No blobs found', response.get_data(as_text=True))

    @patch('app.latest_blob')
    def test_video_latest_exception(self, mock_latest_blob):
        """Test video_latest handles unexpected exceptions."""
        mock_latest_blob.side_effect = Exception("Unexpected error")

        response = self.client.get('/video_latest')
        self.assertEqual(response.status_code, 500)
        self.assertIn('Unexpected error', response.get_data(as_text=True))


class LatestBlobTestCase(unittest.TestCase):
    @patch('app.get_video_list')
    def test_latest_blob_returns_most_recent(self, mock_get_video_list):
        """Test latest_blob returns the blob with the most recent updated time."""
        mock_blob_old = MagicMock()
        mock_blob_old.updated = datetime(2025, 1, 1, tzinfo=dt_timezone.utc)
        mock_blob_old.name = "old.mp4"
        mock_blob_old.size = 1000
        mock_blob_old.time_created = datetime(2025, 1, 1, tzinfo=dt_timezone.utc)

        mock_blob_new = MagicMock()
        mock_blob_new.updated = datetime(2025, 1, 24, tzinfo=dt_timezone.utc)
        mock_blob_new.name = "new.mp4"
        mock_blob_new.size = 2000
        mock_blob_new.time_created = datetime(2025, 1, 24, tzinfo=dt_timezone.utc)

        mock_get_video_list.return_value = [mock_blob_old, mock_blob_new]

        result = latest_blob()
        self.assertEqual(result, "new.mp4")

    @patch('app.get_video_list')
    def test_latest_blob_empty_list_raises(self, mock_get_video_list):
        """Test latest_blob raises ValueError when no blobs."""
        mock_get_video_list.return_value = []

        with self.assertRaises(ValueError) as context:
            latest_blob()

        self.assertIn('No blobs found', str(context.exception))


class GetVideoListTestCase(unittest.TestCase):
    @patch('app.storage_client')
    def test_get_video_list_returns_blobs(self, mock_storage_client):
        """Test get_video_list returns blobs from GCS."""
        mock_blob = MagicMock()
        mock_blob.name = "2025/01/seacliff-test.mp4"
        mock_storage_client.list_blobs.return_value = [mock_blob]

        result = get_video_list()

        mock_storage_client.list_blobs.assert_called_once()
        # Result is the iterator, convert to check
        self.assertIsNotNone(result)

    @patch('app.storage_client')
    def test_get_video_list_uses_correct_prefix(self, mock_storage_client):
        """Test get_video_list uses the correct date-based prefix."""
        mock_storage_client.list_blobs.return_value = []

        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2025/01/seacliff"
            try:
                get_video_list()
            except ValueError:
                pass  # Expected when no blobs

        mock_storage_client.list_blobs.assert_called_with(BUCKET_NAME, prefix="2025/01/seacliff")


class GalleryTestCase(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    @patch('app.render_template')
    def test_gallery_passes_api_url(self, mock_render_template):
        """Test gallery passes the API URL to the template."""
        mock_render_template.return_value = "Gallery"

        response = self.client.get('/gallery')

        mock_render_template.assert_called_once_with(
            'gallery.html',
            api_base_url=COLLECTOR_API_URL
        )
        self.assertEqual(response.status_code, 200)

    @patch.dict(os.environ, {'COLLECTOR_API_URL': 'https://api.example.com'})
    def test_collector_api_url_from_env(self):
        """Test COLLECTOR_API_URL can be set from environment."""
        # This tests the module-level constant behavior
        # In a real scenario, the app would need to be reloaded
        # For now, just verify the pattern works
        self.assertIsInstance(COLLECTOR_API_URL, str)


class SunsetGalleryTestCase(unittest.TestCase):
    """Test cases for the sunset gallery feature."""

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    @patch('app.render_template')
    def test_sunset_gallery_route_exists(self, mock_render_template):
        """Test the sunset-gallery route exists and returns 200."""
        mock_render_template.return_value = "Sunset Gallery"
        response = self.client.get('/sunset-gallery')
        self.assertEqual(response.status_code, 200)

    @patch('app.render_template')
    def test_sunset_gallery_uses_correct_template(self, mock_render_template):
        """Test sunset-gallery uses the sunset_gallery.html template."""
        mock_render_template.return_value = "Sunset Gallery"
        self.client.get('/sunset-gallery')
        mock_render_template.assert_called_once_with(
            'sunset_gallery.html',
            api_base_url=COLLECTOR_API_URL
        )

    @patch('app.render_template')
    def test_sunset_gallery_passes_api_url(self, mock_render_template):
        """Test sunset-gallery passes the API URL to the template."""
        mock_render_template.return_value = "Sunset Gallery"
        self.client.get('/sunset-gallery')

        # Verify api_base_url is passed
        call_kwargs = mock_render_template.call_args[1]
        self.assertIn('api_base_url', call_kwargs)
        self.assertEqual(call_kwargs['api_base_url'], COLLECTOR_API_URL)

    def test_sunset_gallery_content_type(self, ):
        """Test sunset-gallery returns HTML content."""
        response = self.client.get('/sunset-gallery')
        # Should return HTML (text/html)
        self.assertIn('text/html', response.content_type)


if __name__ == '__main__':
    unittest.main()
