
import qianfan
from .base_model_api import BaseLLM
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Ernie(BaseLLM):

    SOTA = 'ERNIE-4.0-8K-Latest'

    MOST_RECOMMENDED_MODEL = ['ERNIE-3.5-8K']

    SUPPORT_MODEL_LIST = [
        'ERNIE-4.0-8K',
        'ERNIE-4.0-8K-Preview',
        'ERNIE-4.0-8K-Preview-0518',
        'ERNIE-4.0-8K-Latest',
        'ERNIE-4.0-8K-0329',
        'ERNIE-4.0-8K-0613',
        'ERNIE-4.0-Turbo-8K',
        'ERNIE-4.0-Turbo-8K-Preview',
        'ERNIE-3.5-8K',
        'ERNIE-3.5-8K-Preview',
        'ERNIE-3.5-8K-0329',
        'ERNIE-3.5-128K',
        'ERNIE-3.5-8K-0613',
        'ERNIE-3.5-8K-0701',
        'ERNIE-Speed-8K',
        'ERNIE-Speed-128K',
        'ERNIE-Character-8K',
        'ERNIE-Character-Fiction-8K',
        'ERNIE-Lite-8K',
        'ERNIE-Lite-8K-0922',
        'ERNIE-Lite-8K-0725',
        'ERNIE-Lite-4K-0704',
        'ERNIE-Lite-4K-0516',
        'ERNIE-Lite-128K-0419',
        'ERNIE-Functions-8K-0321',
        'ERNIE-Tiny-8K',
        'ERNIE-Novel-8K',
        'ERNIE-Speed-AppBuilder-8K',
        'ERNIE-Lite-AppBuilder-8K-0614'
    ]

    def __init__(
        self, 
        api_and_secret_keys : list,
        model_name : str
    ):
        self.clients = [qianfan.ChatCompletion(ak=api_and_secret_key["api_key"], sk=api_and_secret_key["secret_key"]) for api_and_secret_key in api_and_secret_keys]
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
        response = client.do(model=self.model_name, messages=[{
            "role": "user",
            "content": content
        }])

        if response["body"]:
            return response["body"]["result"]
        else:
            raise ValueError("Empty response from API")
    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST