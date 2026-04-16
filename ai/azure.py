import base64
import json
from urllib import parse, request

from openai import AzureOpenAI
from db.MySqlConn import config
from ai import OPENAI_CHAT_COMPLETION_OPTIONS


class AzureAIClient:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=config["AI"]["CHAT_TOKEN"],
            azure_endpoint=config["AI"]["CHAT_BASE"],
            api_version=config["AI"]["CHAT_VERSION"]
        )
        self.image_client = AzureOpenAI(
            api_key=config["AI"]["IMAGE_TOKEN"],
            azure_endpoint=config["AI"]["IMAGE_BASE"],
            api_version=config["AI"]["IMAGE_VERSION"]
        )

    def generate_image(self, prompt) -> bytes | str:
        endpoint = config["AI"]["IMAGE_BASE"].rstrip("/")
        deployment = config["AI"]["IMAGE_MODEL"]
        api_version = config["AI"]["IMAGE_VERSION"]
        api_url = (
            f"{endpoint}/openai/deployments/{deployment}/images/generations?"
            f"{parse.urlencode({'api-version': api_version})}"
        )
        payload = {
            "prompt": prompt,
            "size": "1024x1024",
            "quality": "medium",
            "output_compression": 100,
            "output_format": "png",
            "n": 1
        }
        http_request = request.Request(
            api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config['AI']['IMAGE_TOKEN']}"
            },
            data=json.dumps(payload).encode("utf-8"),
            method="POST"
        )

        with request.urlopen(http_request, timeout=60) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        image_data = response_payload["data"][0]

        if image_data.get("b64_json"):
            return base64.b64decode(image_data["b64_json"])

        if image_data.get("url"):
            return image_data["url"]

        raise ValueError("Azure image generation response missing image data")

    def chat_completions(self, messages: list):
        completion = self.client.chat.completions.create(
            model=OPENAI_CHAT_COMPLETION_OPTIONS["model"],
            messages=messages
        )
        # print(completion.choices[0].message)
        return completion
