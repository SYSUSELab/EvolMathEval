from .base_model_api import BaseLLM
import json
from openai import OpenAI  # <-- 修改为此行
import concurrent.futures
import requests  # <-- 【修改一】确保导入了 requests
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Zhipu(BaseLLM):

    SOTA = 'glm-4-0520'
    BASE_URL = "https://api.agicto.cn/v1/chat/completions"

    MOST_RECOMMENDED_MODEL = ['glm-4-flashx']
    EVALUATION_MODELS = ['glm-4-flash']

    SUPPORT_MODEL_LIST = [
        'glm-4',
        'glm-4-air',
        'glm-4-airx',
        'glm-4-flash',
        'glm-3-turbo',
        'glm-4-0520',
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

        # --- 新增代码：用于进度计算 ---
        total_prompts = len(prompts)
        completed_count = 0
        # --- 新增代码结束 ---

        with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
            future_to_index = {executor.submit(self.generation, prompt, self.api_keys[i % len(self.api_keys)]): i for
                               i, prompt in enumerate(prompts)}

            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]

                # --- 新增代码：更新并打印进度 ---
                completed_count += 1
                # --- 新增代码结束 ---

                try:
                    # 【修改点】接收完整的 response 对象
                    full_response_dict = future.result()

                    # --- 新增代码：打印成功进度 ---
                    print(
                        f"  > [API返回进度] 成功收到第 {completed_count} / {total_prompts} 个结果 (原始请求ID: {index + 1})")
                    # --- 新增代码结束 ---

                    text_result = full_response_dict['choices'][0]['message']['content']

                    # 将正确的结果存入列表
                    results[index] = ("success", text_result, full_response_dict)

                except Exception as exc:
                    # 【修改点】统一错误处理逻辑
                    error_msg = f"请求产生异常: {exc}"

                    results[index] = ("error", error_msg, {"error_message": error_msg})
                    # --- 新增代码：打印失败进度 ---
                    print(
                        f"  > [API返回进度] 第 {completed_count} / {total_prompts} 个结果返回时出错 (原始请求ID: {index + 1}): {exc}")
                    # --- 新增代码结束 ---

        return results

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(6))
    def generation(self, content, api_key, temperature=0.3):  # <-- client 参数变为 api_key
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            # 您可以按需保留 temperature 等参数
        }
        try:
            response = requests.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            if response.status_code != 200:
                error_msg = f"API error ({response.status_code}): {response.text}"
                raise ValueError(error_msg)
            response_data = response.json()

            if ('choices' not in response_data or
                    not response_data['choices'] or
                    'message' not in response_data['choices'][0] or
                    'content' not in response_data['choices'][0]['message']):
                raise ValueError(f"Unexpected response format: {response.text}")
            return response_data
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Request failed: {str(e)}")

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST
