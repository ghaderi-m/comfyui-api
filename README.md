# 📦 ComfyUI API Client (in progress)

A Python client for interacting with [ComfyUI](https://github.com/comfyanonymous/ComfyUI) via its HTTP API. This tool sends prompt workflows, monitors execution, and retrieves generated images for local use or optional cloud upload.

> 🧪 Based on `websockets_api_example.py` from the official [ComfyUI script examples](https://github.com/comfyanonymous/ComfyUI/tree/master/script_examples)

---

## 🚀 Features

- ✅ Load custom workflow from JSON (`workflow.json`)
- ✅ Inject your own **prompt text** at runtime
- ✅ Upload images via local file path **or HTTP URL**
- ✅ Submit prompt and monitor progress via `/prompt` and `/history`
- ✅ Download, display, and optionally save output images
- ✅ Upload output images to **Amazon S3**
- ✅ Fully configurable via `.env` file and CLI arguments

---

## 📦 Installation

Create a virtual environment and install dependencies using poetry:

```bash
peotry install
```

Create a `.env` file for your config (you can start from `.env.example`):

```bash
cp .env.example .env
```

---

## ⚙️ Environment Variables (`.env`)

```env
# ComfyUI Server
SERVER_ADDRESS=127.0.0.1:8188
DEFAULT_WORKFLOW=workflow1.json
SAVE_IMAGES=yes

# Optional: Upload output to S3
UPLOAD_TO_S3=no
S3_BUCKET_NAME=your-bucket
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
AWS_REGION=us-west-2
S3_ENDPOINT_URL=https://s3.us-west-2.amazonaws.com
```

---

## 🧪 Usage

### Basic run with defaults

```bash
python main.py
```

### Use a custom workflow

```bash
python main.py --workflow workflow2.json
```

### Set a custom prompt dynamically

```bash
python main.py --prompt "A Hyper realistic 3d render of a car"
```

### Upload image from local file (used in the workflow)

```bash
python main.py --upload_image /path/to/image.jpg
```

### Upload image from remote URL

```bash
python main.py --upload_image https://example.com/image.jpg
```

### Save output images locally and to S3

```bash
UPLOAD_TO_S3=yes python main.py --prompt "A hyper realistic render of a car"
```

### Disable local saving

```bash
python main.py --nosave
```

---

## 📁 Output

Images will be saved to:

```
saved_images/<prompt_id>/<node>_<index>.png
```

And optionally uploaded to:

```
s3://<your-bucket>/comfyui/<prompt_id>/<node>_<index>.png
```

---

## 🛠 Example Workflow Patch

This client automatically:
- Injects your prompt into the first `CLIPTextEncode` node
- Replaces the `LoadImage` node input with uploaded file (or URL)

No manual edits to `workflow.json` are needed.

---

## 🧼 Coming Soon (Ideas)

- Multi-prompt batching
- Async support
- Auto-cleanup for old local files
- More node patching (e.g., VAE, UNET)

---

