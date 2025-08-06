from .base_model_api import BaseLLM
import requests
import concurrent.futures
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Deepseek(BaseLLM):
    # --- 以下为Deepseek的模型信息 ---
    SOTA = 'deepseek-r1-250528'

    MOST_RECOMMENDED_MODEL = [
        'deepseek-v3-0324',
    ]

    SUPPORT_MODEL_LIST = [
        'deepseek-v3-0324',
        'deepseek-coder'
    ]

    EVALUATION_MODELS = [
        # 'deepseek-v3-0324',
        # 'deepseek-r1-250528'
        'deepseek-r1',
    ]

    # --- 以下代码逻辑完全复制自 Qwen 类 ---

    # BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    BASE_URL = "https://api.agicto.cn/v1/chat/completions"
    def __init__(
            self,
            api_keys: list,
            model_name: str
    ):
        self.api_keys = api_keys
        self.model_name = model_name

    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)
        total_prompts = len(prompts)
        completed_count = 0
        # 可以根据需要调整 max_workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
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
                    # 'future.result()'现在是一个完整的字典
                    full_response_dict = future.result()
                    print(
                        f"  > [API返回进度] 成功收到第 {completed_count} / {total_prompts} 个结果 (原始请求ID: {index + 1})")

                    # 1. 从字典中提取出模型生成的文本
                    text_result = full_response_dict['choices'][0]['message']['content']

                    # 2. 完整的回复本身就已经是我们需要的字典了

                    # 3. 将结果存储为标准的三元素元组格式
                    results[index] = ("success", text_result, full_response_dict)

                except Exception as exc:
                    # 确保失败时也返回同样格式的三元素元组
                    error_msg = f"请求产生异常: {exc}"
                    results[index] = ("error", error_msg, {"error_message": error_msg})
                    print(
                        f"  > [API返回进度] 第 {completed_count} / {total_prompts} 个结果返回时出错 (原始请求ID: {index + 1}): {exc}")
        return results

    @retry(wait=wait_random_exponential(min=1, max=4), stop=stop_after_attempt(2))
    def generation(self, content, api_key):
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # 注意：这里的payload结构是完全按照Qwen的格式。
        # 如果Deepseek的API需要不同的字段（比如没有enable_thinking），可能需要调整。
        # 但根据您的要求“代码逻辑全部用qwen的”，此处保持原样。
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            # "enable_thinking": False
        }

        response = requests.post(
            self.BASE_URL,
            headers=headers,
            json=payload,
            timeout=2000
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
            # 在返回前，先检查回复是否有效
            if not response_data.get('choices') or not response_data['choices'][0].get('message', {}).get('content'):
                raise ValueError("从API收到了无效或空的回复：缺少'content'字段。")
            # 返回完整的JSON字典
            return response_data
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"无效的回复格式: {str(e)}")

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST