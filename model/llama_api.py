from .base_model_api import BaseLLM
from openai import OpenAI
import concurrent.futures
from tenacity import retry, wait_random_exponential, stop_after_attempt

class Llama(BaseLLM):

    SOTA = "Llama-3.1-405b"

    MOST_RECOMMENDED_MODEL = ["llama3-70b-8192","llama3-8b-8192"]
    EVALUATION_MODELS = [
        # "llama3-70b-8192",
        "llama3-8b-8192"
    ]

    SUPPORT_MODEL_LIST = [
        "llama-guard-3-8b",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "Llama-3.1-405b",
        "Llama-3.1-70b",
        "Llama-3.1-8b",
        "Llama-3-70b-chat-hf",
        "Llama-3-8b-chat-hf",
        "Llama-2-7b-chat-hf",
        "Llama-2-13b-chat-hf",
        "Llama-2-70b-chat-hf",
        "CodeLlama-7b-Instruct-hf",
        "CodeLlama-70b-Instruct-hf",
        "CodeLlama-34b-Instruct-hf",
        "CodeLlama-13b-Instruct-hf",
        "llama2-70b-4096"
    ]

    def __init__(
        self, 
        api_keys : list,
        model_name : str
    ):
        self.clients = [OpenAI(api_key=api_key, base_url="https://api.agicto.cn/v1") for api_key in api_keys]
        self.model_name = model_name

    def generation_in_parallel(self, prompts):
        results = [None] * len(prompts)  # 初始化一个与prompts长度相同的列表，用于存放结果
        total_prompts = len(prompts)
        completed_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_index = {executor.submit(self.generation, prompt, self.clients[i % len(self.clients)]): i for i, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                completed_count += 1
                try:
                    # 【修改点】接收完整的 response 对象
                    full_response_object = future.result()

                    # --- 新增代码：打印成功进度 ---
                    print(
                        f"  > [API返回进度] 成功收到第 {completed_count} / {total_prompts} 个结果 (原始请求ID: {index + 1})")
                    # --- 新增代码结束 ---

                    # 1. 从对象中提取文本结果
                    text_result = full_response_object.choices[0].message.content

                    # 2. 【修改点】将完整的 Pydantic 对象转为字典，用于获取 token 等信息
                    full_response_dict = full_response_object.model_dump()

                    # 3. 【修改点】将结果打包成标准的三元素元组
                    results[index] = ("success", text_result, full_response_dict)

                except Exception as exc:
                    # 【修改点】统一错误处理逻辑
                    error_msg = f"请求产生异常: {exc}"

                    # --- 新增代码：打印失败进度 ---
                    results[index] = ("error", error_msg, {"error_message": error_msg})
                    print(
                        f"  > [API返回进度] 第 {completed_count} / {total_prompts} 个结果返回时出错 (原始请求ID: {index + 1}): {exc}")
                    # --- 新增代码结束 ---
        return results

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(5))
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
        # if not response.choices or not response.choices[0].message.content:
        #     print("\n---------- DEBUG: Problematic API Response Detected ----------")
        #     print("--- Request Prompt (first 100 chars):")
        #     print(content[:100] + "...")  # 打印出问题的prompt的前100个字符
        #     print("--- Raw API Response:")
        #     print(response.model_dump_json(indent=2))  # 打印服务器返回的原始JSON

        # 【修改点】检查响应是否有效，然后返回整个对象，而不是只返回文本
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("从API收到了无效或空的回复")
        return response  # <-- 返回完整的 response 对象

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST