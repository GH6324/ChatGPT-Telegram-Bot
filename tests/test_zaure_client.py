import unittest
import sys
import types
from unittest.mock import patch, MagicMock

fake_openai = types.ModuleType('openai')
fake_openai.AzureOpenAI = MagicMock()
sys.modules.setdefault('openai', fake_openai)

fake_mysql_conn = types.ModuleType('db.MySqlConn')
fake_mysql_conn.config = {
    "AI": {
        "CHAT_TOKEN": "chat-token",
        "CHAT_BASE": "https://example.openai.azure.com",
        "CHAT_VERSION": "2024-05-01-preview",
        "IMAGE_TOKEN": "image-token",
        "IMAGE_BASE": "https://example.openai.azure.com",
        "IMAGE_VERSION": "2025-04-01-preview",
        "IMAGE_MODEL": "gpt-image-1",
        "MODEL": "gpt-4o"
    }
}
sys.modules.setdefault('db.MySqlConn', fake_mysql_conn)

from ai.azure import AzureAIClient


class TestAzureAIClient(unittest.TestCase):
    @patch('ai.azure.request.urlopen')
    @patch('ai.azure.AzureOpenAI')
    def test_generate_image_returns_decoded_bytes(self, MockAzureOpenAI, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": [{"b64_json": "aGVsbG8="}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = AzureAIClient()

        result = client.generate_image("fox")

        self.assertEqual(result, b"hello")
        mock_urlopen.assert_called_once()

    @patch('ai.azure.AzureOpenAI')
    def test_chat_completions(self, MockAzureOpenAI):
        # Mock the AzureOpenAI client and its methods
        mock_client = MockAzureOpenAI.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message={"role": "assistant", "content": "Recursion is fun."})]
        mock_client.chat.completions.create.return_value = mock_response

        # Create an instance of AzureAIClient
        client = AzureAIClient()

        # Define test inputs
        messages = [{"role": "user", "content": "Write a haiku about recursion in programming."}]

        # Call the chat_completions method and collect results
        result = client.chat_completions(messages)

        # Verify the results
        self.assertEqual(result.choices[0].message["content"], "Recursion is fun.")


if __name__ == '__main__':
    unittest.main()
