from .base_model_api import BaseLLM
import requests
import concurrent.futures
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt


class Qwen3(BaseLLM):
    # SOTA = 'qwen3-32b'
    BASE_URL = "https://api.agicto.cn/v1/chat/completions"

    MOST_RECOMMENDED_MODEL = ['qwen3-32b']

    SUPPORT_MODEL_LIST = [
    ]

    def __init__(
            self,
            api_keys: list,
            model_name: str
    ):
        self.api_keys = api_keys
        self.model_name = model_name

    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.api_keys)) as executor:
            future_to_index = {
                executor.submit(
                    self.generation,
                    prompt,
                    self.api_keys[i % len(self.api_keys)]  # 使用API key轮询
                ): i
                for i, prompt in enumerate(prompts)
            }
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    data = future.result()
                    results[index] = (prompts[index], data)
                except Exception as exc:
                    results[index] = (prompts[index], f"Request generated an exception: {exc}")
        return results

    @retry(wait=wait_random_exponential(min=1, max=4), stop=stop_after_attempt(2))
    def generation(self, content, api_key):
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            "enable_thinking": False
        }

        response = requests.post(
            self.BASE_URL,
            headers=headers,
            json=payload,
            timeout=300  # 添加超时防止永久等待
        )

        # 检查HTTP状态码
        if response.status_code != 200:
            error_msg = f"API error ({response.status_code}): {response.text}"
            raise ValueError(error_msg)

        try:
            response_data = response.json()
            content = response_data['choices'][0]['message']['content']
            return content
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid response format: {str(e)}")

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST