from .base_model_api import BaseLLM
from openai import OpenAI
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Openai(BaseLLM):

    SOTA = "gpt-4-turbo-2024-04-09"

    MOST_RECOMMENDED_MODEL = ["gpt-4o-mini"]

    SUPPORT_MODEL_LIST = [
        "gpt-4o-2024-08-06",
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo-preview",
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-32k",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-0314",
        "dall-e-3",
        "dall-e-2",
        "gpt-4",
        "gpt-4-1106-vision-preview",
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "gpt-3.5-turbo-0301",
        "gpt-3.5-turbo-16k-0613",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo-instruct",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo"
    ]
    
    def __init__(
        self, 
        api_keys : list,
        model_name : str
    ):
        self.clients = [OpenAI(api_key=api_key, base_url = "https://api.agicto.cn/v1") for api_key in api_keys]
        self.model_name = model_name

    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)  # 初始化一个与prompts长度相同的列表，用于存放结果
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            future_to_index = {executor.submit(self.generation, prompt, self.clients[i % len(self.clients)]): i for i, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    data = future.result()
                    results[index] = (prompts[index], data)  # 按照原始索引位置存放结果
                except Exception as exc:
                    results[index] = (prompts[index], f"Request generated an exception: {exc}")
    
        return results

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(6))
    def generation(self, content, client, temperature=0.3):
        response = client.chat.completions.create(
            model=self.model_name, 
            messages=[
                {
                    "role": "user", 
                    "content": content
                }
            ]
        )
        if response.choices[0].message.content:
            return response.choices[0].message.content 
        else:
            raise ValueError("Empty response from API")
    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST
