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
    EVALUATION_MODELS = [
        "gpt-3.5-turbo",
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
        total_prompts = len(prompts)  # 获取请求总数
        completed_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            future_to_index = {executor.submit(self.generation, prompt, self.clients[i % len(self.clients)]): i for i, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                completed_count += 1
                try:
                    # 'full_response_object' is the complete object from the 'generation' method
                    full_response_object = future.result()
                    print(f"  > [API返回进度] 成功收到第 {completed_count} / {total_prompts} 个结果 (原始请求ID: {index + 1})")

                    # 1. Extract the generated text from the response
                    text_result = full_response_object.choices[0].message.content

                    # 2. Convert the entire Pydantic response object to a dictionary
                    full_response_dict = full_response_object.model_dump()

                    # 3. Store the structured result
                    results[index] = ("success", text_result, full_response_dict)
                except Exception as exc:
                    # 【重要修正】确保失败时也返回三元组，保持格式一致
                    error_msg = f"Request generated an exception: {exc}"
                    results[index] = ("error", error_msg, {"error_message": error_msg})
                    print(f"  > [API返回进度] 第 {completed_count} / {total_prompts} 个结果返回时出错 (原始请求ID: {index + 1}): {exc}")

        return results

    @retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def generation(self, content, client, temperature=0.3):
        # --- vvv 在此处添加新的调试代码 vvv ---
        # 可以在请求前打印信息，这部分总是安全的
        # print("\n" + "=" * 80)
        # print(f"[调试信息] 准备发起请求... (部分内容: '{content[:80]}...')")
        # print(f"[调试信息] 使用模型: {self.model_name}, Temperature: {temperature}")
        # --- ^^^ 添加完毕 ^^^ ---
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )

        # --- vvv 在此处添加正确的调试代码 vvv ---
        # 成功获取响应后，打印其内容
        # 使用 model_dump_json() 可以得到一个格式优美的JSON字符串，非常适合调试
        # print(f"[调试信息] API 成功返回, 原始返回内容 (JSON格式):")
        # print(response.model_dump_json(indent=2))
        # print("=" * 80 + "\n")
        # --- ^^^ 添加完毕 ^^^ ---
        # 【重要修正】检查逻辑保持，但返回整个 response 对象
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Empty or invalid response from API")
        return response
        # if response.choices[0].message.content:
        #     return response.choices[0].message.content
        # else:
        #     raise ValueError("Empty response from API")

    def support_model_list(self):
        return self.SUPPORT_MODEL_LIST





# from .base_model_api import BaseLLM
# import requests  # 导入 requests 库
# import concurrent.futures
# import json
# from tenacity import retry, wait_random_exponential, stop_after_attempt
#
# class Openai(BaseLLM):
#
#     # --- 以下为 OpenAI 的模型信息 (保持不变) ---
#     SOTA = "gpt-4-turbo-2024-04-09"
#
#     MOST_RECOMMENDED_MODEL = ["gpt-4o-mini"]
#
#     SUPPORT_MODEL_LIST = [
#         "gpt-4o-2024-08-06", "gpt-4o-mini", "gpt-4o", "gpt-4-turbo-preview", "gpt-4-turbo",
#         "gpt-4-turbo-2024-04-09", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-0613", "gpt-4-0314",
#         "dall-e-3", "dall-e-2", "gpt-4", "gpt-4-1106-vision-preview", "gpt-4-1106-preview",
#         "gpt-4-0125-preview", "gpt-3.5-turbo-0301", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-16k",
#         "gpt-3.5-turbo-instruct", "gpt-3.5-turbo-0613", "gpt-3.5-turbo-0125", "gpt-3.5-turbo-1106",
#         "gpt-3.5-turbo"
#     ]
#     EVALUATION_MODELS = [
#         # "gpt-3.5-turbo",
#         "o3",
#     ]
#
#     # --- 以下代码逻辑完全模仿自 Qwen 类 ---
#
#     # 【模仿点】使用与 Qwen 相同的 BASE_URL 格式
#     BASE_URL = "https://api.agicto.cn/v1/chat/completions"
#
#     # 【模仿点】__init__ 方法与 Qwen 完全相同
#     def __init__(
#             self,
#             api_keys: list,
#             model_name: str
#     ):
#         self.api_keys = api_keys
#         self.model_name = model_name
#
#     # 【模仿点】generation_in_parallel 方法与 Qwen 完全相同
#     def generation_in_parallel(self, prompts):
#         results = [None] * len(prompts)
#         total_prompts = len(prompts)
#         completed_count = 0
#         # 注意：这里的 max_workers 可以根据需要调整，此处沿用 Qwen 的 40
#         with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
#             future_to_index = {
#                 executor.submit(
#                     self.generation,
#                     prompt,
#                     self.api_keys[i % len(self.api_keys)]
#                 ): i
#                 for i, prompt in enumerate(prompts)
#             }
#             for future in concurrent.futures.as_completed(future_to_index):
#                 index = future_to_index[future]
#                 completed_count += 1
#                 try:
#                     # 'future.result()'现在是一个完整的字典
#                     full_response_dict = future.result()
#                     print(f"  > [API返回进度] 成功收到第 {completed_count} / {total_prompts} 个结果 (原始请求ID: {index + 1})")
#
#                     # 1. 从字典中提取出模型生成的文本
#                     text_result = full_response_dict['choices'][0]['message']['content']
#
#                     # 2. 完整的回复本身就已经是我们需要的字典了
#
#                     # 3. 将结果存储为标准的三元素元组格式
#                     results[index] = ("success", text_result, full_response_dict)
#
#                 except Exception as exc:
#                     # 确保失败时也返回同样格式的三元素元组
#                     error_msg = f"请求产生异常: {exc}"
#                     results[index] = ("error", error_msg, {"error_message": error_msg})
#                     print(f"  > [API返回进度] 第 {completed_count} / {total_prompts} 个结果返回时出错 (原始请求ID: {index + 1}): {exc}")
#         return results
#
#     # 【模仿点】generation 方法的结构、逻辑和 tenacity 设置与 Qwen 完全相同
#     @retry(wait=wait_random_exponential(min=1, max=4), stop=stop_after_attempt(2))
#     def generation(self, content, api_key):
#         headers = {
#             'Authorization': f'Bearer {api_key}',
#             'Content-Type': 'application/json'
#         }
#
#         # 构造请求体，注意 OpenAI API 没有 enable_thinking 参数，因此将其移除
#         payload = {
#             "model": self.model_name,
#             "messages": [{"role": "user", "content": content}],
#         }
#
#         # 使用 requests.post 发送请求
#         response = requests.post(
#             self.BASE_URL,
#             headers=headers,
#             json=payload,
#             timeout=300
#         )
#         # # --- vvv 在此处添加新的调试代码 vvv ---
#         # print("\n" + "=" * 80)
#         # print(f"[调试信息] 正在尝试请求... (部分内容: '{content[:50]}...')")
#         # print(f"[调试信息] API 返回状态码: {response.status_code}")
#         print(f"[调试信息] API 原始返回内容 (response.text):")
#         print(response.text)  # 这里打印的就是您想要的原始返回串
#         print("=" * 80 + "\n")
#         # # --- ^^^ 添加完毕 ^^^ ---
#
#         # 检查 HTTP 状态码
#         if response.status_code != 200:
#             error_msg = f"API error ({response.status_code}): {response.text}"
#             raise ValueError(error_msg)
#
#         try:
#             # 解析 JSON 响应
#             response_data = response.json()
#             # 检查回复内容是否有效
#             if not response_data.get('choices') or not response_data['choices'][0].get('message', {}).get('content'):
#                 raise ValueError("从API收到了无效或空的回复：缺少'content'字段。")
#             # 返回完整的JSON字典
#             return response_data
#         except (KeyError, IndexError, json.JSONDecodeError) as e:
#             raise ValueError(f"无效的回复格式: {str(e)}")
#
#     # 【模仿点】support_model_list 方法与 Qwen 完全相同
#     def support_model_list(self):
#         return self.SUPPORT_MODEL_LIST