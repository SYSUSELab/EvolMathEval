from .base_model_api import BaseLLM
import requests
import concurrent.futures
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Moonshot(BaseLLM):

    # --- Moonshot's model information (preserved) ---
    SOTA = 'moonshot-v1-8k'

    MOST_RECOMMENDED_MODEL = ["moonshot-v1-8k"]

    SUPPORT_MODEL_LIST = [
        'moonshot-v1-8k',
        'moonshot-v1-32k',
        'moonshot-v1-128k'
    ]

    EVALUATION_MODELS = [
        'Moonshot-Kimi-K2-Instruct',
    ]

    # --- Code logic now mimics the standardized class structure ---

    # Set the target URL for the API endpoint
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    # Rewritten __init__ to simply store API keys as strings
    def __init__(
            self,
            api_keys: list,
            model_name: str
    ):
        self.api_keys = [""]
        self.model_name = model_name

    # Rewritten to handle results as ("success", text, dict) or ("error", msg, dict)
    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)
        total_prompts = len(prompts)
        completed_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {
                executor.submit(
                    self.generation,
                    prompt,
                    self.api_keys[i % len(self.api_keys)]
                ): i
                for i, prompt in enumerate(prompts)
            }
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                completed_count += 1
                try:
                    full_response_dict = future.result()
                    print(
                        f"  > [API返回进度] 成功收到第 {completed_count} / {total_prompts} 个结果 (原始请求ID: {index + 1})")

                    text_result = full_response_dict['choices'][0]['message']['content']

                    results[index] = ("success", text_result, full_response_dict)

                except Exception as exc:
                    error_msg = f"请求产生异常: {exc}"
                    results[index] = ("error", error_msg, {"error_message": error_msg})
                    print(
                        f"  > [API返回进度] 第 {completed_count} / {total_prompts} 个结果返回时出错 (原始请求ID: {index + 1}): {exc}")
        return results

    # Rewritten to use 'requests' and return the full JSON dictionary
    @retry(wait=wait_random_exponential(min=1, max=4), stop=stop_after_attempt(2))
    def generation(self, content, api_key):
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
        }

        response = requests.post(
            self.BASE_URL,
            headers=headers,
            json=payload,
            timeout=1000
        )
        # --- vvv 在此处添加新的调试代码 vvv ---
        print("\n" + "=" * 80)
        print(f"[调试信息] 正在尝试请求... (部分内容: '{content[:50]}...')")
        print(f"[调试信息] API 返回状态码: {response.status_code}")
        print(f"[调试信息] API 原始返回内容 (response.text):")
        print(response.text)  # 这里打印的就是您想要的原始返回串
        print("=" * 80 + "\n")
        # --- ^^^ 添加完毕 ^^^ ---

        if response.status_code != 200:
            error_msg = f"API error ({response.status_code}): {response.text}"
            raise ValueError(error_msg)

        try:
            response_data = response.json()
            if not response_data.get('choices') or not response_data['choices'][0].get('message', {}).get('content'):
                raise ValueError("从API收到了无效或空的回复：缺少'content'字段。")

            return response_data
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"无效的回复格式: {str(e)}")

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST