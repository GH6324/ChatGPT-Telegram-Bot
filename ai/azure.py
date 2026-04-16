import base64
import json
import requests
from typing import Union, Optional
from io import BytesIO

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

    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "medium", n: int = 1) -> Union[bytes, str]:
        """
        Generate image using Azure OpenAI DALL-E
        
        Args:
            prompt: Image generation prompt
            size: Image size (default: "1024x1024")
            quality: Image quality ("standard" or "medium")
            n: Number of images to generate (default: 1)
            
        Returns:
            Image data as bytes or URL string
        """
        ai_config = config["AI"]
        endpoint = ai_config["IMAGE_BASE"].rstrip("/")
        deployment = ai_config["IMAGE_MODEL"]
        api_version = ai_config["IMAGE_VERSION"]
        
        # Build API URL
        generation_url = f"{endpoint}/openai/deployments/{deployment}/images/generations?api-version={api_version}"
        
        # Prepare request body
        body = {
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": "png",
            "n": n
        }
        
        # Try authentication methods
        headers = self._get_image_auth_headers()
        last_error = None
        
        for header in headers:
            try:
                response = requests.post(
                    generation_url,
                    headers=header,
                    json=body,
                    timeout=60
                )
                response.raise_for_status()
                response_data = response.json()
                break
            except requests.exceptions.HTTPError as exc:
                last_error = exc
                # Only retry on auth errors
                if exc.response.status_code not in (401, 403):
                    raise exc
        else:
            # All auth methods failed
            if last_error and "AuthenticationTypeDisabled" in str(last_error.response.text):
                raise ValueError(
                    "Azure key-based auth is disabled for image generation. "
                    "Set AI.IMAGE_AUTH_TYPE to 'bearer' and provide AI.IMAGE_BEARER_TOKEN "
                    "(Microsoft Entra access token for https://cognitiveservices.azure.com/.default)."
                )
            raise last_error
        
        # Extract image data
        image_data = response_data["data"][0]
        
        if image_data.get("b64_json"):
            return base64.b64decode(image_data["b64_json"])
        
        if image_data.get("url"):
            return image_data["url"]
        
        raise ValueError("Azure image generation response missing image data")
    
    def edit_image(
        self,
        prompt: str,
        image_data: bytes,
        mask_data: Optional[bytes] = None,
        size: str = "1024x1024",
        quality: str = "medium",
        n: int = 1
    ) -> Union[bytes, str]:
        """
        Edit image using Azure OpenAI DALL-E
        
        Args:
            prompt: Image editing prompt
            image_data: Original image as bytes
            mask_data: Optional mask image as bytes (transparent areas will be edited)
            size: Image size (default: "1024x1024")
            quality: Image quality ("standard" or "medium")
            n: Number of images to generate (default: 1)
            
        Returns:
            Edited image data as bytes or URL string
        """
        ai_config = config["AI"]
        endpoint = ai_config["IMAGE_BASE"].rstrip("/")
        deployment = ai_config["IMAGE_MODEL"]
        api_version = ai_config["IMAGE_VERSION"]
        
        # Build API URL
        edit_url = f"{endpoint}/openai/deployments/{deployment}/images/edits?api-version={api_version}"
        
        # Prepare request body
        data = {
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": n
        }
        
        # Prepare files
        files = {
            "image": ("image.png", BytesIO(image_data), "image/png")
        }
        
        if mask_data:
            files["mask"] = ("mask.png", BytesIO(mask_data), "image/png")
        
        # Get auth headers (exclude Content-Type for multipart/form-data)
        headers = self._get_image_auth_headers(include_content_type=False)
        last_error = None
        
        for header in headers:
            try:
                response = requests.post(
                    edit_url,
                    headers=header,
                    data=data,
                    files=files,
                    timeout=60
                )
                response.raise_for_status()
                response_data = response.json()
                break
            except requests.exceptions.HTTPError as exc:
                last_error = exc
                # Only retry on auth errors
                if exc.response.status_code not in (401, 403):
                    raise exc
        else:
            # All auth methods failed
            if last_error:
                raise last_error
        
        # Extract image data
        image_data = response_data["data"][0]
        
        if image_data.get("b64_json"):
            return base64.b64decode(image_data["b64_json"])
        
        if image_data.get("url"):
            return image_data["url"]
        
        raise ValueError("Azure image edit response missing image data")

    def _get_image_auth_headers(self, include_content_type: bool = True):
        """
        Build authentication headers for Azure image API
        
        Args:
            include_content_type: Whether to include Content-Type header
            
        Returns:
            List of header dictionaries to try (supports auth fallback)
        """
        ai_config = config["AI"]
        api_key = ai_config.get("IMAGE_TOKEN", "")
        bearer_token = ai_config.get("IMAGE_BEARER_TOKEN") or api_key
        auth_type = ai_config.get("IMAGE_AUTH_TYPE", "auto").strip().lower()
        
        if auth_type not in ("auto", "api_key", "bearer"):
            auth_type = "auto"
        
        headers_list = []
        base_headers = {"Content-Type": "application/json"} if include_content_type else {}
        
        # Try API key auth
        if auth_type in ("auto", "api_key") and api_key:
            headers_list.append({
                **base_headers,
                "api-key": api_key
            })
        
        # Try Bearer token auth
        if auth_type in ("auto", "bearer") and bearer_token:
            headers_list.append({
                **base_headers,
                "Authorization": f"Bearer {bearer_token}"
            })
        
        if not headers_list:
            raise ValueError(
                "No valid Azure image auth header could be built. "
                "Check IMAGE_AUTH_TYPE and tokens in config."
            )
        
        return headers_list

    def chat_completions(self, messages: list):
        completion = self.client.chat.completions.create(
            model=OPENAI_CHAT_COMPLETION_OPTIONS["model"],
            messages=messages
        )
        # print(completion.choices[0].message)
        return completion
