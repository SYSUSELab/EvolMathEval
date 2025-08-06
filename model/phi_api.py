from .base_model_api import BaseLLM
from openai import OpenAI
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Phi(BaseLLM):

    SOTA = 'phi3'

    SUPPORT_MODEL_LIST = [
        'phi3', 
        'Phi-3-mini', 
        'Phi-3-small', 
        'Phi-3-medium'
    ]


    def __init__(
        self, 
        api_keys : list,
        model_name : str
    ):
        self.clients = [OpenAI(api_key=api_key, base_url="http://localhost:11434/v1") for api_key in api_keys]
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