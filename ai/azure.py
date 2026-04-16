import base64
import json
from typing import Union
from urllib.error import HTTPError
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

    def generate_image(self, prompt) -> Union[bytes, str]:
        ai_config = config["AI"]
        endpoint = config["AI"]["IMAGE_BASE"].rstrip("/")
        deployment = config["AI"]["IMAGE_MODEL"]
        api_version = config["AI"]["IMAGE_VERSION"]
        image_api_key = ai_config.get("IMAGE_TOKEN", "")
        image_bearer_token = ai_config.get("IMAGE_BEARER_TOKEN") or image_api_key
        image_auth_type = ai_config.get("IMAGE_AUTH_TYPE", "auto")
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
        last_error = None
        auth_headers = self._build_image_auth_headers(
            image_api_key,
            image_bearer_token,
            image_auth_type
        )

        if not auth_headers:
            raise ValueError("No valid Azure image auth header could be built. Check IMAGE_AUTH_TYPE and tokens.")

        for headers in auth_headers:
            http_request = request.Request(
                api_url,
                headers=headers,
                data=json.dumps(payload).encode("utf-8"),
                method="POST"
            )

            try:
                with request.urlopen(http_request, timeout=60) as response:
                    response_payload = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                last_error = HTTPError(
                    exc.url,
                    exc.code,
                    f"{exc.reason}: {error_body}",
                    exc.headers,
                    None
                )
                if exc.code not in (401, 403):
                    raise last_error
        else:
            if last_error and "AuthenticationTypeDisabled" in str(last_error):
                raise ValueError(
                    "Azure key-based auth is disabled for image generation. "
                    "Set AI.IMAGE_AUTH_TYPE to 'bearer' and provide AI.IMAGE_BEARER_TOKEN "
                    "(Microsoft Entra access token for https://cognitiveservices.azure.com/.default)."
                )
            raise last_error

        image_data = response_payload["data"][0]

        if image_data.get("b64_json"):
            return base64.b64decode(image_data["b64_json"])

        if image_data.get("url"):
            return image_data["url"]

        raise ValueError("Azure image generation response missing image data")

    @staticmethod
    def _build_image_auth_headers(api_key, bearer_token, auth_type="auto"):
        mode = (auth_type or "auto").strip().lower()
        if mode not in ("auto", "api_key", "bearer"):
            mode = "auto"

        headers = []
        if mode in ("auto", "api_key") and api_key:
            headers.append({
                "Content-Type": "application/json",
                "api-key": api_key
            })

        if mode in ("auto", "bearer") and bearer_token:
            headers.append({
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bearer_token}"
            })

        return headers

    def chat_completions(self, messages: list):
        completion = self.client.chat.completions.create(
            model=OPENAI_CHAT_COMPLETION_OPTIONS["model"],
            messages=messages
        )
        # print(completion.choices[0].message)
        return completion
