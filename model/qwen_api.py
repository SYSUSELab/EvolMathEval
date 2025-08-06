from .base_model_api import BaseLLM
import requests
import concurrent.futures
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt


class Qwen(BaseLLM):
    SOTA = 'qwen3-32b'
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    MOST_RECOMMENDED_MODEL = ['qwen3-235b-a22b', 'qwen3-32b', 'qwen3-30b-a3b']

    # EVALUATION_MODELS = ['qwen3-32b']
    EVALUATION_MODELS = [
        # 'qwen3-32b',
        # 'qwen3-30b-a3b',
        'qwen3-235b-a22b',
    ]

    SUPPORT_MODEL_LIST = [
        'qwen2-57b-a14b-instruct',
        'qwen2-72b-instruct',
        'qwen2-7b-instruct',
        'qwen2-1.5b-instruct',
        'qwen2-0.5b-instruct',
        'qwen1.5-110b-chat',
        'qwen1.5-72b-chat',
        'qwen1.5-32b-chat',
        'qwen1.5-14b-chat',
        'qwen1.5-7b-chat',
        'qwen1.5-1.8b-chat',
        'qwen1.5-0.5b-chat',
        'codeqwen1.5-7b-chat',
        'qwen-72b-chat',
        'qwen-14b-chat',
        'qwen-7b-chat',
        'qwen-1.8b-longcontext-chat',
        'qwen-1.8b-chat',
        'qwen-plus',
        'qwen-turbo',
        'qwen-max'
    ]

    def __init__(
            self,
            api_keys: list,
            model_name: str
    ):
        self.api_keys = [""]
        self.model_name = model_name

    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)
        total_prompts = len(prompts)
        completed_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
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
                    # 【修改点】'future.result()'现在是一个完整的字典
                    full_response_dict = future.result()
                    print(f"  > [API返回进度] 成功收到第 {completed_count} / {total_prompts} 个结果 (原始请求ID: {index + 1})")

                    # 1. 从字典中提取出模型生成的文本
                    text_result = full_response_dict['choices'][0]['message']['content']

                    # 2. 完整的回复本身就已经是我们需要的字典了

                    # 3. 【核心】将结果存储为标准的三元素元组格式
                    results[index] = ("success", text_result, full_response_dict)

                except Exception as exc:
                    # 【核心】确保失败时也返回同样格式的三元素元-组
                    error_msg = f"请求产生异常: {exc}"
                    results[index] = ("error", error_msg, {"error_message": error_msg})
                    print(f"  > [API返回进度] 第 {completed_count} / {total_prompts} 个结果返回时出错 (原始请求ID: {index + 1}): {exc}")
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
            timeout=300
        )

        if response.status_code != 200:
            error_msg = f"API error ({response.status_code}): {response.text}"
            raise ValueError(error_msg)

        try:
            response_data = response.json()
            # 【重要】在返回前，先检查回复是否有效
            if not response_data.get('choices') or not response_data['choices'][0].get('message', {}).get('content'):
                raise ValueError("从API收到了无效或空的回复：缺少'content'字段。")
            # 【修改点】返回完整的JSON字典
            return response_data
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"无效的回复格式: {str(e)}")

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST