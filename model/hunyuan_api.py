from model.base_model_api import BaseLLM
import concurrent.futures
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Hunyuan(BaseLLM):
    SOTA = 'hunyuan-pro'

    MOST_RECOMMENDED_MODEL = ['hunyuan-pro']


    SUPPORT_MODEL_LIST = [
        'hunyuan-lite',
        'hunyuan-standard',
        'hunyuan-standard-256K',
        'hunyuan-pro',
        'hunyuan-code',
    ]

    def __init__(
            self,
            secret_id_and_keys: list,
            model_name: str
    ):
        self.clients = [hunyuan_client.HunyuanClient(credential.Credential(secret_id_and_key['secret_id'], secret_id_and_key['secret_key']), "")
                        for secret_id_and_key in secret_id_and_keys]
        self.model_name = model_name

    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)  # 初始化一个与prompts长度相同的列表，用于存放结果
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            future_to_index = {executor.submit(self.generation, prompt, self.clients[i % len(self.clients)]): i for
                               i, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    data = future.result()
                    results[index] = (prompts[index], data)  # 按照原始索引位置存放结果
                except Exception as exc:
                    results[index] = (prompts[index], f"Request generated an exception: {exc}")

        return results

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(6))
    def generation(self, content, client, temperature=1):
        try:
            req = models.ChatCompletionsRequest()
            params = {
                "Messages": [{"Role": "user", "Content": content}],
                "Model": self.model_name,
            }
            req.from_json_string(json.dumps(params))
            resp = client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except TencentCloudSDKException as err:
            print(err)

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST
