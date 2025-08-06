from .base_model_api import BaseLLM
from openai import OpenAI
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt
import requests
import json

class Yunqi(BaseLLM):

    SOTA = ""

    MOST_RECOMMENDED_MODEL = []

    SUPPORT_MODEL_LIST = []
    
    def __init__(
        self, 
        api_keys : list,
        model_name : str
    ):
        self.api_keys = api_keys
        self.url = 'http://47.52.23.21:8803/robot/v1/speak/temporary'
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
        # 定义请求数据
        data = {
            "prompt": content,
        }

        # 发送 POST 请求
        response = requests.post(self.url, data=data)

        if response.status_code == 200:
            return response.json()["data"]["response"]
        else:
            raise ValueError("Empty response from API")
        

    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST
