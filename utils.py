import os
import json
import logging
import tempfile
import boto3
import urllib.request
from urllib.parse import urlparse
from botocore.exceptions import BotoCoreError, NoCredentialsError
from typing import Tuple


def get_s3_config():
    return {
        "bucket": os.getenv("S3_BUCKET_NAME"),
        "access_key": os.getenv("S3_ACCESS_KEY"),
        "secret_key": os.getenv("S3_SECRET_KEY"),
        "region": os.getenv("AWS_REGION", "us-west-2"),
        "endpoint": os.getenv("S3_ENDPOINT_URL"),
        "enabled": os.getenv("UPLOAD_TO_S3", "no").lower() in ("1", "true", "yes", "y"),
    }


def str2bool(value: str) -> bool:
    return str(value).lower() in ("yes", "true", "1", "y")


def load_workflow(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Workflow file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def patch_prompt_text_node(workflow: dict, prompt_text: str) -> None:
    """
    Replaces 'text' input of the first CLIPTextEncode node that is the positive prompt and not a negative prompt.
    Skips nodes with 'negative' in their _meta title.
    """
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == "CLIPTextEncode":
            title = node.get("_meta", {}).get("title", "").lower()
            if "negative" in title:
                continue  # Skip negative prompt node
            inputs = node.get("inputs", {})
            if "text" in inputs:
                logging.info(f"Patching CLIPTextEncode node {node_id} (title: {title}) with new prompt.")
                inputs["text"] = prompt_text
                return
    raise ValueError("No suitable CLIPTextEncode node (non-negative) with 'text' input found in workflow.")


def patch_load_image_node(workflow: dict, image_info: dict) -> None:
    for node_id, node in workflow.items():
        if node.get("class_type") == "LoadImage":
            if "image" in node.get("inputs", {}):
                logging.info(f"Patching LoadImage node {node_id} with uploaded image filename.")
                node["inputs"]["image"] = image_info["name"]
                return
    raise ValueError("No LoadImage node with 'image' input found in workflow.")


def ensure_folder(path: str):
    os.makedirs(path, exist_ok=True)


def upload_to_s3(image_bytes: bytes, bucket_name: str, object_key: str, region: str,
                 access_key: str, secret_key: str, endpoint_url: str = None):
    try:
        session = boto3.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        s3 = session.client("s3", endpoint_url=endpoint_url)

        s3.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=image_bytes,
            ContentType="image/png"
        )
        logging.info(f"Uploaded to S3: s3://{bucket_name}/{object_key}")
    except (BotoCoreError, NoCredentialsError) as e:
        logging.error(f"Failed to upload to S3: {e}")


def get_image_file(server_address: str, filename: str, subfolder: str, folder_type: str) -> bytes:
    query = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type
    })
    url = f"http://{server_address}/view?{query}"
    with urllib.request.urlopen(url) as response:
        return response.read()


def prepare_image_for_upload(image_path: str) -> Tuple[str, str, str]:
    """
    Handles image input from either URL or local path.
    Returns (upload_path, filename, mime_type).
    If it's a URL, downloads to a temporary file.
    """
    is_url = urlparse(image_path).scheme in ("http", "https")

    if is_url:
        response = urllib.request.urlopen(image_path)
        suffix = os.path.splitext(image_path)[-1] or ".jpg"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(response.read())
        temp_file.close()
        return temp_file.name, os.path.basename(urlparse(image_path).path), "image/png"
    else:
        return image_path, os.path.basename(image_path), "image/png"


def upload_input_image(image_path: str, server_address: str) -> dict:
    """
    Uploads an image (from local path or URL) to the ComfyUI /upload/image endpoint.
    """
    from requests import post

    upload_path, filename, mime_type = prepare_image_for_upload(image_path)
    url = f"http://{server_address.rstrip('/')}/upload/image"

    try:
        with open(upload_path, 'rb') as img_file:
            files = {'image': (filename, img_file, mime_type)}
            data = {'overwrite': 'true', 'type': 'input'}
            response = post(url, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            logging.info(f"Uploaded image to ComfyUI: {result}")
            return result
    finally:
        # Clean up temp file if applicable
        if upload_path != image_path and os.path.exists(upload_path):
            os.unlink(upload_path)
