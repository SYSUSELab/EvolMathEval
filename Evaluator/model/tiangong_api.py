from .base_model_api import BaseLLM
from openai import OpenAI
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt
import requests
import json
import time
import hashlib

class Tiangong(BaseLLM):

    SOTA = ""

    MOST_RECOMMENDED_MODEL = [""]

    SUPPORT_MODEL_LIST = [""]
    
    def __init__(
        self, 
        api_keys : list,
        model_name : str
    ):
        self.api_keys = api_keys
        self.url = 'https://api-maas.singularity-ai.com/sky-work/api/v1/chat'
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

    # @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(6))
    def generation(self, content, api_key, temperature=0.3):
        
        app_key = api_key["app_key"]
        app_secret = api_key["app_secret"]

        timestamp = str(int(time.time()))
        sign_content = app_key + app_secret + timestamp
        sign_result = hashlib.md5(sign_content.encode('utf-8')).hexdigest()


        # 设置请求头，请求的数据格式为json
        headers={
            "app_key": app_key,
            "timestamp": timestamp,
            "sign": sign_result,
            "Content-Type": "application/json",
        }

        # 设置请求URL和参数
        data = {
            "messages": [
                {"role": "user", "content": content}
            ],
            "intent" : "chat"
        }

        # 发起请求并获取响应
        response = requests.post(self.url, headers=headers, json=data, stream=False)

        if response.status_code == 200:
            ans = ""
            # 处理响应流
            for line in response.iter_lines():
                if line:
                    # 处理接收到的数据
                    try:
                        ans += (json.loads(line.decode('utf-8')[5:])["arguments"][0]["messages"][0]["text"])
                    except:
                        return ans
            return ans
        else:
            print("error")
            raise ValueError("Empty response from API")
        

    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST

