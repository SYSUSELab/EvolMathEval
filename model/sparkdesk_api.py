from .base_model_api import BaseLLM
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

class Sparkdesk(BaseLLM):

    SOTA = 'Spark4.0 Ultra'

    MOST_RECOMMENDED_MODEL = ['Spark Lite']

    SUPPORT_MODEL_LIST = [
        'Spark4.0 Ultra', 'Spark Max', 'Spark Pro', 'Spark Pro-128K', 'Spark Lite'
    ]

    MODEL_TO_URL_AND_DOMAIN = {
        'Spark4.0 Ultra' : {
            "url" : "wss://spark-api.xf-yun.com/v4.0/chat",
            "domain" : "4.0Ultra"
        },
        'Spark Max' : {
            "url" : "wss://spark-api.xf-yun.com/v3.5/chat",
            "domain" : "generalv3.5"
        },
        'Spark Pro-128K' : {
            "url" : "wss://spark-api.xf-yun.com/chat/pro-128k",
            "domain" : "pro-128k"
        },
        'Spark Pro' : {
            "url" : "wss://spark-api.xf-yun.com/v3.1/chat",
            "domain" : "generalv3"
        },
        'Spark Lite' : {
            "url" : "wss://spark-api.xf-yun.com/v1.1/chat",
            "domain" : "general"
        }
    }

    def __init__(
        self, 
        api_and_secret_key_and_ids : list,
        model_name : str
    ):  
        self.clients = [ChatSparkLLM(
            spark_api_url = self.MODEL_TO_URL_AND_DOMAIN[model_name]["url"],
            spark_app_id=api_and_secret_key_and_id["app_id"],
            spark_api_key=api_and_secret_key_and_id["api_key"],
            spark_api_secret=api_and_secret_key_and_id["secret_key"],
            spark_llm_domain=self.MODEL_TO_URL_AND_DOMAIN[model_name]["domain"],
            streaming=False,
        ) for api_and_secret_key_and_id in api_and_secret_key_and_ids]


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
        messages = [ChatMessage(role="user",content=content)]
        response = client.generate([messages])

        if response.generations[0][0].text:
            return response.generations[0][0].text
        else:
            raise ValueError("Empty response from API")
    
    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST