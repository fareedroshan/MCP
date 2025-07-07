import unittest
from unittest.mock import patch, MagicMock
import os
import json

from src.ai_agent.llm.llm_query_engine import LLMQueryEngine

class TestLLMQueryEngine(unittest.TestCase):

    def setUp(self):
        self.api_key = "fake_api_key"
        # Patch os.getenv for OPENAI_API_KEY if LLMQueryEngine uses it directly for default
        self.getenv_patcher = patch.dict(os.environ, {"OPENAI_API_KEY": self.api_key})
        self.getenv_patcher.start()
        self.addCleanup(self.getenv_patcher.stop)

    def test_init_with_api_key(self):
        engine = LLMQueryEngine(api_key=self.api_key)
        self.assertEqual(engine.api_key, self.api_key)
        self.assertEqual(engine.model, "gpt-4o") # Default model

    def test_init_with_env_var_api_key(self):
        # Relies on setUp's patch.dict
        engine = LLMQueryEngine()
        self.assertEqual(engine.api_key, self.api_key)

    def test_init_no_api_key(self):
        # Temporarily remove the API key from env for this test
        with patch.dict(os.environ, clear=True):
            with self.assertRaisesRegex(ValueError, "OpenAI API key not provided"):
                LLMQueryEngine()

    def test_generate_prompt(self):
        engine = LLMQueryEngine(api_key=self.api_key)
        user_query = "Install NTP"
        device_context = {"os_type": "linux", "hostname": "server1"}

        system_message, prompt = engine.generate_prompt(user_query, device_context)

        self.assertIn("You are an AI agent", system_message)
        self.assertIn(json.dumps(device_context, indent=2), prompt)
        self.assertIn(f'User Query: "{user_query}"', prompt)

    @patch('openai.chat.completions.create')
    def test_query_llm_success(self, mock_openai_create):
        mock_response_content = "sudo apt update\nsudo apt install ntp -y"
        mock_choice = MagicMock()
        mock_choice.message.content = mock_response_content
        mock_api_response = MagicMock()
        mock_api_response.choices = [mock_choice]
        mock_openai_create.return_value = mock_api_response

        engine = LLMQueryEngine(api_key=self.api_key, model="gpt-test")
        user_query = "Install NTP"
        device_context = {"os_type": "linux"}

        response = engine.query_llm(user_query, device_context)

        self.assertEqual(response, mock_response_content)
        mock_openai_create.assert_called_once()
        called_args, called_kwargs = mock_openai_create.call_args
        self.assertEqual(called_kwargs['model'], "gpt-test")

        messages = called_kwargs['messages']
        self.assertEqual(messages[0]['role'], "system")
        self.assertEqual(messages[1]['role'], "user")
        self.assertIn(user_query, messages[1]['content'])
        self.assertIn(json.dumps(device_context, indent=2), messages[1]['content']) # Added indent=2


    @patch('openai.chat.completions.create')
    def test_query_llm_no_choices(self, mock_openai_create):
        mock_api_response = MagicMock()
        mock_api_response.choices = [] # No choices returned
        mock_openai_create.return_value = mock_api_response

        engine = LLMQueryEngine(api_key=self.api_key)
        response = engine.query_llm("test query", {})

        self.assertIsNone(response) # Or specific error/message based on implementation

    @patch('openai.chat.completions.create')
    def test_query_llm_api_error(self, mock_openai_create):
        mock_openai_create.side_effect = Exception("API communication error")

        engine = LLMQueryEngine(api_key=self.api_key)
        response = engine.query_llm("test query", {})

        self.assertIsNone(response) # Or specific error/message

if __name__ == '__main__':
    unittest.main()
