import os
import requests
import re
import time
import random
import httpx
from typing import List, Dict, Any
from openai import OpenAI
from openai.types.responses.response import Response

from .constants import strip_cot_reminders_from_history


class LLMPlayer:

    def __init__(self, model_config: Dict[str, Any]):
        """
        Initialize LLM player
        Args:
            model_config: Configuration dict with endpoint, api_key_env, model_name, etc.
        """
        self.model_config = model_config

        api_key = os.getenv('api_key_env')
        self.api_key = api_key

        if not api_key:
            raise ValueError(f"API key not found in environment variable api_key_env")

        endpoint = model_config.get('endpoint')
        http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=api_key,
            base_url=endpoint,
            http_client=http_client
        )
        
        self.model_name = model_config['model_name']
        self.raw_responses = []
        self.additional_chat_kwargs = model_config['additional_chat_kwargs'] if 'additional_chat_kwargs' in model_config else {}
        self.messages: List[Dict[str, str]] = []
        self.completion_tokens = 0
        self.prompt_tokens = 0
        self.price = 0
    
    @staticmethod
    def _is_empty_response(text: Any) -> bool:
        return text is None or not str(text).strip()

    def initialize_player_with_prompts(self, system_prompt: str, initial_user_message: str):
        """
        Initialize a new game first user message

        Args:
            initial_user_message: The first user message to start the game
        """
        self.messages = [
            {"role": "user", "content": f"{system_prompt}\n{initial_user_message}".strip()}
        ]

    def _get_move_once(self) -> str:
        """
        Single attempt to get response from LLM.
        Raises ValueError if response is empty or None.
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.messages,
            **self.additional_chat_kwargs
        )
        self.raw_responses.append(response)

        assistant_message = response.choices[0].message.content

        if self._is_empty_response(assistant_message):
            raise ValueError("OpenAI-compatible API returned empty or None content")

        usage = getattr(response, "usage", None)
        if usage is not None:
            self.completion_tokens += getattr(usage, "completion_tokens", 0) or 0
            self.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.price += getattr(usage, "cost", 0) or 0

        return assistant_message.strip()
    
    def _clear_cot_reminders(self):
        strip_cot_reminders_from_history(self.messages, key='content')

    def get_move(self) -> str:
        """
        Get the next move from the LLM

        Returns:
            The LLM's response
        """
        assert self.messages[-1]["role"] == "user"

        self._clear_cot_reminders()

        last_exception = None

        MAX_ATTEMPTS = 6

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                assistant_message = self._get_move_once()

                if self._is_empty_response(assistant_message):
                    raise ValueError("LLM returned empty or None response")

                return assistant_message

            except Exception as e:
                last_exception = e
                print(
                    f"\nError getting LLM response "
                    f"(attempt {attempt}/{MAX_ATTEMPTS}): {e}"
                )

                if attempt < MAX_ATTEMPTS + 1:
                    sleep_time = random.randint(5, 20)
                    time.sleep(sleep_time)

        raise RuntimeError(
            f"Failed to get non-empty LLM response after {MAX_ATTEMPTS} attempts"
        ) from last_exception
    
    def add_player_history(self, message: str):
        self.messages.append({
            "role": "assistant",
            "content": message
        })

    def add_feedback(self, feedback: str):
        self.messages.append({
            "role": "user",
            "content": feedback
        })
    
    def get_message_history(self) -> List[Dict[str, str]]:
        return self.messages.copy()
    
    def reset(self):
        self.messages = []
