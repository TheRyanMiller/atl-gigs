try:
    import boto3  # type: ignore
except ImportError:  # Optional; only needed for R2 upload/download
    boto3 = None

from scraper import config


def download_from_r2(key, local_path):
    """
    Download a file from R2 if it exists.
    Returns True if downloaded, False if not found or error.
    """
    if not boto3:
        return False

    if not all([config.R2_ACCOUNT_ID, config.R2_ACCESS_KEY_ID, config.R2_SECRET_ACCESS_KEY]):
        return False

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
        )

        response = s3.get_object(Bucket=config.R2_BUCKET_NAME, Key=key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(response["Body"].read())
        return True
    except Exception:
        return False


def upload_to_r2(log_func=None):
    """
    Upload all event data files to Cloudflare R2.
    Returns True if successful, False otherwise.
    log_func: optional logging function (defaults to print)
    """
    log = log_func or print

    if not boto3:
        log("R2 upload skipped: boto3 not installed")
        return False

    if not all([config.R2_ACCOUNT_ID, config.R2_ACCESS_KEY_ID, config.R2_SECRET_ACCESS_KEY]):
        log("R2 upload skipped: missing R2 credentials")
        return False

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
        )

        uploaded = []

        def put(path, key, content_type):
            if path.exists():
                with open(path, "rb") as f:
                    s3.put_object(
                        Bucket=config.R2_BUCKET_NAME,
                        Key=key,
                        Body=f.read(),
                        ContentType=content_type,
                    )
                uploaded.append(key)

        put(config.OUTPUT_PATH, "events.json", "application/json")
        put(config.STATUS_PATH, "scrape-status.json", "application/json")
        put(config.SEEN_CACHE_PATH, "seen-cache.json", "application/json")
        put(config.ARTIST_CACHE_PATH, "artist-cache.json", "application/json")
        put(config.SPOTIFY_CACHE_PATH, "artist-spotify-cache.json", "application/json")

        log(f"Uploaded to R2: {', '.join(uploaded)}")
        return True
    except Exception as e:
        log(f"R2 upload failed: {e}")
        return False
