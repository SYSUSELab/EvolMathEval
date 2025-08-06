from .base_model_api import BaseLLM
import sensenova
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Sensechat(BaseLLM):

    SOTA = 'SenseChat-5'

    MOST_RECOMMENDED_MODEL = ['SenseChat-Turbo']

    SUPPORT_MODEL_LIST = [
        'SenseChat-5',
        'SenseChat',
        'SenseChat-32K',
        'SenseChat-128K',
        'SenseChat-Turbo'
    ]


    def __init__(
        self, 
        api_keys : dict,
        model_name : str
    ):
        sensenova.access_key_id = api_keys[0]["access_key_id"]
        sensenova.secret_access_key = api_keys[0]["secret_access_key"]
        self.model_name = model_name

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(6))
    def generation(self, content, temperature=0.8):
        response = sensenova.ChatCompletion.create(
            messages=[{"role": "user", "content": content}],
            model=self.model_name,
            temperature=temperature,
        )
        if response['data']['choices'][0].message:
            return response['data']['choices'][0].message  
        else:
            raise ValueError("Empty response from API")
    
    def generation_in_parallel(self, prompts):
        results = []
        for prompt in prompts:
            try:
                results.append((prompt, self.generation(prompt)))
            except Exception as exc:
                results.append((prompt, f"Request generated an exception: {exc}"))
        return results
    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST