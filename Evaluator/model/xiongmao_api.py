from .base_model_api import BaseLLM
from openai import OpenAI
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt
import requests
import json

class Xiongmao(BaseLLM):

    SOTA = ""

    MOST_RECOMMENDED_MODEL = []

    SUPPORT_MODEL_LIST = []
    
    def __init__(
        self, 
        api_keys : list,
        model_name : str
    ):
        self.api_keys = api_keys
        self.model_name = model_name
        self.get_access_token()
        self.get_global_sessionID()

    def get_access_token(self):
        url = "https://open.ai.pandalaw.cn/api/token/obtain"

        # 定义查询参数
        params = {
            "appKey": self.api_keys[0]["app_key"],
            "appSecret": self.api_keys[0]["app_secret"]
        }

        # 发送带参数的GET请求
        response = requests.get(url, params=params)
        # print(response.text)
        self.accessToken = response.json()["data"]["accessToken"]

    def get_global_sessionID(self):
        url = "https://open.ai.pandalaw.cn/api/session/create"

        # 定义查询参数
        params = {
            "accessToken": self.accessToken,
            "extData": "{\"userId\":\"1001\"}"
        }

        # 发送带参数的GET请求
        response = requests.post(url, params=params)
        # print(response.text)
        self.gsid = response.json()["data"]["gsid"]

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
        
        headers = {
            'accessToken': self.accessToken,
            'gsid': self.gsid
        }
        
        # 定义请求数据
        data = {
            "type": "ZNWD",
        }

        # 建立session
        response = requests.post("https://open.ai.pandalaw.cn/api/chat/session/create", headers=headers, data=data)
        # print(response.text)
        sid = response.json()["data"]["sid"]

        # 发送 POST 请求
        data = {
            "sid" : sid,
            "question" : content
        }
        response = requests.post("https://open.ai.pandalaw.cn/api/chat/sse/ask", headers=headers, data=data)
        response = json.loads(response.text[5:].split("\n")[0].strip())
        # print(response)
        # print("---")
        if response["code"] == 200:
            return response["data"]
        else:
            raise ValueError("Empty response from API")
        

    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST
