import argparse
import logging
import os
from dotenv import load_dotenv
from comfy_client import ComfyUIClient
from utils import (
    load_workflow, str2bool, patch_load_image_node,
    patch_prompt_text_node, upload_input_image
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()


def get_env_defaults():
    return {
        "server": os.getenv("SERVER_ADDRESS", "127.0.0.1:8188"),
        "workflow": os.getenv("DEFAULT_WORKFLOW", "workflow1.json"),
        "save_images": str2bool(os.getenv("SAVE_IMAGES", "yes")),
    }


def parse_arguments(defaults):
    parser = argparse.ArgumentParser(description="ComfyUI API Client")
    parser.add_argument("--workflow", type=str, default=defaults["workflow"], help="Path to workflow JSON file")
    parser.add_argument("--prompt", type=str, help="Prompt text to inject into the workflow")
    parser.add_argument("--server", type=str, default=defaults["server"], help="ComfyUI server address (host:port)")
    parser.add_argument("--save", action="store_true", default=defaults["save_images"], help="Save images to disk")
    parser.add_argument("--nosave", action="store_false", dest="save", help="Do not save images")
    parser.add_argument("--upload_image", type=str, help="Path or URL of image to upload and inject into workflow")
    return parser.parse_args()


def run_prompt_pipeline(args):
    workflow = load_workflow(args.workflow)
    client = ComfyUIClient(args.server)

    if args.upload_image:
        upload_info = upload_input_image(args.upload_image, client.server_address)
        patch_load_image_node(workflow, upload_info)

    if args.prompt:
        patch_prompt_text_node(workflow, args.prompt)

    images, prompt_id = client.get_images(workflow)

    if args.save:
        client.save_images(images, prompt_id)

    client.display_images(images)


def main():
    try:
        defaults = get_env_defaults()
        args = parse_arguments(defaults)
        run_prompt_pipeline(args)
    except Exception as e:
        logging.error(f"Execution failed: {e}")


if __name__ == "__main__":
    main()
