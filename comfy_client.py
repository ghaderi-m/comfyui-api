import uuid
import json
import urllib.request
import urllib.parse
import urllib.error
import time
import os
import io
import logging
from typing import Dict, List
from PIL import Image

from utils import (
    ensure_folder,
    upload_to_s3,
    str2bool,
    get_s3_config,
    get_image_file
)


class ComfyUIClient:
    def __init__(self, server_address: str):
        self.server_address = server_address.rstrip("/")
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, prompt: dict) -> str:
        url = f"http://{self.server_address}/prompt"
        headers = {"Content-Type": "application/json"}
        data = json.dumps({"prompt": prompt}).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read())["prompt_id"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            logging.error(f"HTTP {e.code}: {e.reason} | {error_body}")
            raise

    def get_history(self, prompt_id: str) -> dict:
        url = f"http://{self.server_address}/history/{prompt_id}"
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read())

    def wait_for_execution(self, prompt_id: str, timeout: int = 300, interval: int = 5) -> dict:
        start_time = time.time()
        logging.info(f"Waiting for prompt {prompt_id} to complete...")

        while time.time() - start_time < timeout:
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history and history[prompt_id].get("outputs"):
                    logging.info("Prompt execution completed.")
                    return history[prompt_id]["outputs"]
            except Exception as e:
                logging.warning(f"Polling error: {e}")
            time.sleep(interval)

        raise TimeoutError("Prompt execution timed out.")

    def get_images(self, prompt: dict) -> (Dict[str, List[bytes]], str):
        prompt_id = self.queue_prompt(prompt)
        outputs = self.wait_for_execution(prompt_id)
        images: Dict[str, List[bytes]] = {}

        for node_id, output in outputs.items():
            node_images = []
            for image in output.get("images", []):
                image_data = get_image_file(self.server_address, image["filename"], image["subfolder"], image["type"])
                node_images.append(image_data)
            images[node_id] = node_images

        return images, prompt_id

    def display_images(self, images: Dict[str, List[bytes]]):
        for node_id, image_list in images.items():
            for idx, data in enumerate(image_list, 1):
                image = Image.open(io.BytesIO(data))
                logging.info(f"Displaying image {idx} from node {node_id}")
                image.show()

    def save_images(self, images: Dict[str, List[bytes]], prompt_id: str):
        output_dir = os.path.join("saved_images", prompt_id)
        ensure_folder(output_dir)

        s3_enabled = str2bool(os.getenv("UPLOAD_TO_S3", "no"))
        s3_config = get_s3_config() if s3_enabled else None

        for node_id, image_list in images.items():
            for idx, data in enumerate(image_list, 1):
                filename = f"{node_id}_{idx}.png"
                local_path = os.path.join(output_dir, filename)

                image = Image.open(io.BytesIO(data))
                image.save(local_path)
                logging.info(f"Saved image: {local_path}")

                if s3_enabled and s3_config:
                    s3_key = f"comfyui/{prompt_id}/{filename}"
                    upload_to_s3(
                        image_bytes=data,
                        bucket_name=s3_config["bucket"],
                        object_key=s3_key,
                        region=s3_config["region"],
                        access_key=s3_config["access_key"],
                        secret_key=s3_config["secret_key"],
                        endpoint_url=s3_config["endpoint"]
                    )
