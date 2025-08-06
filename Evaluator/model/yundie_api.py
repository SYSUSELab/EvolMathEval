from .base_model_api import BaseLLM
from openai import OpenAI
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt
import requests
import json

class Yundie(BaseLLM):

    SOTA = ""

    MOST_RECOMMENDED_MODEL = []

    SUPPORT_MODEL_LIST = []
    
    def __init__(
        self, 
        api_keys : list,
        model_name : str
    ):
        self.api_keys = api_keys
        self.url = 'http://www.yisai.top/api/v1/chat/completions'
        self.model_name = model_name

    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)  # 初始化一个与prompts长度相同的列表，用于存放结果
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.api_keys)) as executor:
            future_to_index = {executor.submit(self.generation, prompt, self.api_keys[i % len(self.api_keys)]): i for i, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    data = future.result()
                    results[index] = (prompts[index], data)  # 按照原始索引位置存放结果
                except Exception as exc:
                    results[index] = (prompts[index], f"Request generated an exception: {exc}")
    
        return results

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(6))
    def generation(self, content, api_key, temperature=0.3):
        # 定义请求头
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # 定义请求数据
        data = {
            "chatId": "123",
            "stream": False,
            "detail": False,
            "messages": [
                {
                    "content": content,
                    "role": "user"
                }
            ]
        }

        # 发送 POST 请求
        response = requests.post(self.url, headers=headers, data=json.dumps(data))
        # print(response.text)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"] 
        else:
            print("error")
            raise ValueError("Empty response from API")
        

    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST
