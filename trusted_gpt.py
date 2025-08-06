# -*- coding: utf-8 -*-
import os
import json
import concurrent.futures
from model.openai_api import Openai
from model.base_model_api import generation_result
from model.base_model_api import show_model_list
import model.config as config
from datetime import datetime
import template
import importlib.util
import argparse
import random
import re
from postprocessor import structure_response_into_data

import concurrent.futures  # <--- 在这里添加这一行

class DatasetLoader:
    def __init__(self, file_path, sample_size):
        """
        初始化 DatasetLoader，接受文件路径作为参数
        :param file_path: 数据集文件的路径
        :param sample_size: 采样数量
        """
        self.file_path = file_path
        self.sample_size = sample_size
        self.data = []

    def load_data(self):
        """
        读取指定路径的json文件并解析内容
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件路径不存在: {self.file_path}")

        if self.file_path.endswith('.json'):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                try:
                    file_data = json.load(f)
                    if isinstance(file_data, list):
                        if self.sample_size == -1:
                            self.data = file_data  # 默认评测全部
                        else:
                            self.data = random.sample(file_data, self.sample_size)  # 随机采样
                    else:
                        raise ValueError(f"文件格式错误: {self.file_path}, 内容应为列表")
                except json.JSONDecodeError as e:
                    raise ValueError(f"JSON解析错误: {self.file_path}, 错误信息: {str(e)}")
        else:
            raise ValueError(f"文件不是一个JSON文件: {self.file_path}")

    def get_data(self):
        """
        返回已加载的数据
        :return: 解析后的数据列表
        """
        return self.data


class Task:
    def __init__(self, task_name):
        """
        初始化 Task 类，接受任务名称作为参数
        :param task_name: 任务名称，用于匹配任务的 instruction
        """
        self.task_name = task_name
        self.instruction = None
        self.confusion_map = {
            "≈": "is approximately equal to",
            ">?": "might be greater than",
            "<?": "might be less than",
            "~": "is related to",
            "?": "is possibly related to",
            "=>": "could imply",
            "<-": "could be derived from",
            "??": "the relationship is unclear",
            "...": "somehow results in",
            "∝": "is possibly proportional to",
            "<=>?": "is perhaps equivalent to"
        }

        # 定义任务指令字典，微分、积分、矩阵、向量、复数、概率、极限、级数求和、对数、指数、四舍五入、三角函数、排列组合、概率
        self.task_instructions = {# 和读取的文件相对应
            # "UselessCondition": "请用变量 a、b、c 各出现至少一次，设计三个结构和运算形式尽量不同的数学公式(必须是等式)。公式可以包含加法、减法、乘法、除法或括号运算,里面要包含任意的常数。三个公式之间必须用“#”隔开，请直接回复新增的三个公式，不要添加任何额外内容：",
            "UselessCondition": "Generate three distinct mathematical equations following these strict rules:Content: Each equation must contain the variables a, b, and c. The equations should have diverse structures, using a mix of operations (+, -, *, /), parentheses, and must contain constants.Output Format: You must output all three equations in a single line, separated only by the # symbol.Do not use any numbering, bullet points, or any introductory text. The output must be nothing but the three equations and their separators:",
            # "ConfusedCondition": "请设计两个具有符号迷惑性的数学条件(必须是等式)，要求使用变量 x、y、z，条件中必须使用模糊或不明确的数学符号，从这里选择（\"≈\": \"差不多是\",\">?\": \"说不定比……大\",\"<?\": \"或许不如\",\"?\": \"也许有关\",\"=>\": \"可能意味着\",\"->\": \"可以变成\",\"<-\": \"回过头是\",\"??\": \"说不清楚\",\"...\": \"等等\",）。两个条件之间用“#”隔开，请直接回复新增的两个条件，不要添加任何其他内容：",
            "ConfusedCondition": "Please design two mathematical confusing conditions (must be equations). You are required to use the variables x, y, and z. The conditions must use vague or ambiguous mathematical symbols selected from here: (\"≈\": \"is approximately equal to\", \">?\": \"might be greater than\", \"<?\": \"might be less than\",\"~\": \"is related to\",\"?\": \"is possibly related to\",\"=>\": \"could imply\",\"<-\": \"could be derived from\",\"??\": \"the relationship is unclear\",\"...\": \"somehow results in\",\"∝\": \"is possibly proportional to\",\"<=>?\": \"is perhaps equivalent to\",). You must output the two relationships on a single line.They must be separated only by the # symbol.Do not add any numbering, bullet points, or any text other than the two relationships and the separator:",
            # "FormulaClarifier": "请你把下面的比较生硬的变量之间的关系表达翻译的更加清晰且生动，相关数字请用阿拉伯数字，不可以使用文字表达（例如“二十四”等），不要局限于简单表述，可以使用更加复杂的表达方式，但是注意变量之间的关系必须要保持完全不变，请务必注意每个系数或者符号，绝对不可以忽略任何一个细节，也不要随意添加变量等内容，务必确保润色后仍具有精确性，每个条件之间用句号分隔开，不要标注条件的序号，不要输出其他任何内容，内容如下：",
            "FormulaClarifier": "Please translate the following mathematical formulas into natural English descriptions. The goal is to be descriptive and precise, using varied sentence structures while ensuring the mathematical relationships remain unchanged.CRITICAL RULES:Arabic Numerals ONLY: This is the most important rule. All numbers must be written as digits (e.g., 24, -5, 0.5). Never write numbers as words (e.g., \"twenty-four\").Accuracy is Paramount: Pay close attention to every coefficient and symbol, especially negative signs. Do not add or omit any information.No Parentheses: Do not output the parentheses that identify variables.One Condition, One Sentence: Separate each translated condition with a period. Do not number them.Your output must ONLY be the translated sentences.Now, translate the following content following all rules precisely:",
            # "MisleadingCondition": "我现在想为一道题目添加两个误导性的条件，请根据以下实体和相关的同主题实体，生成两个在逻辑上含糊但不改变解答路径的干扰条件：使用“它”“这个”代词指代某个特定对象，但在前文中提到的多个实体之间没有明确标明指代对象。创建两个数字条件，通过使用时间、顺序提示语等，将它们表面连接起来，但它们的逻辑并不相关。确保这些条件在阅读时能够引起思考，但不需要特别推翻题目本身的解答过程，例如不要明确指出题目相关的实体之间的代数关系。增加一些细节，让解答者注意细节但不至于产生无法解答的混乱。请仅输出两个新增条件，每个条件之间用“#”分隔，不添加任何额外说明，也不需要加顺序标号。",
            "MisleadingCondition": "I want to add two misleading conditions to a problem. Based on the provided entities and other related entities within the same topic, generate two distractor conditions that are logically ambiguous but do not alter the solution path: Use a pronoun such as \"it\" or \"this\" to refer to a specific object, but its antecedent is not clearly specified among the multiple entities mentioned earlier. Create two numerical conditions and superficially link them using temporal or sequential cues (e.g., 'then', 'afterwards'), but they are not logically related. Ensure these conditions provoke thought upon reading but do not fundamentally alter the original solution process for the problem; for instance, do not explicitly state an algebraic relationship between the relevant entities. Incorporate details that draw the solver's attention but do not create unsolvable confusion. Strict Output Format:Output only the two new distractor conditions.Separate them with a single # symbol.Do not include any numbering, explanations, or other text:",
            # "ContextGen": "接下来请你帮我输出下面这个数学题的背景信息，要求符合逻辑，字数在100字以内，请直接回复新增的背景信息，不要添加任何其他内容：",
            "ContextGen": "Please provide the background information for the following math problem. The information must be logical and under 100 words. Please reply directly with only the new background information and do not add any other content:",
            # "AddCondition": "请生成3个数学题的随机条件（每个条件之间用“#”分隔）。条件需要在不同的复杂科幻场景中，但不要给出问题。只需要条件，不要产生任何额外输出，也不需要加顺序标号",
            "AddCondition": "Please generate 3 random conditions for math problems (separate each condition with a \"#\"). The conditions need to be set in different, complex science-fiction scenarios, but do not provide a question. Only the conditions are needed, do not produce any extra output, and do not add sequential numbering.",
        }
        # 变异

        # 获取对应的任务指令
        self._match_task()

    def _match_task(self):
        """
        匹配任务指令并存储到类属性中
        """
        self.instruction = self.task_instructions.get(self.task_name)
        if not self.instruction:
            raise ValueError(f"任务 {self.task_name} 未找到对应的 instruction")

    def get_instruction(self):
        """
        获取任务的指令
        :return: 任务指令字符串
        """
        return self.instruction


class Inferrence:
    def __init__(self, data, task_obj, input_path, output_path,task_name):
        """
        初始化 Inferrence 类
        :param data: 任务数据列表
        :param task_obj: 完整的 Task 对象 <--- 修改点
        :param input_path: 输入文件路径
        :param output_path: 输出文件保存路径
        """
        self.data = data
        self.task_obj = task_obj  # <-- 存储整个 task 对象
        self.instruction = task_obj.get_instruction() # <-- instruction 可以从 task 对象中获取
        self.input_path = input_path
        self.output_path = output_path
        self.task = task_name # <-- 使用新的参数名
        self.model_classes = {}  # 存储模型类
        self.model_instances = {}  # 存储模型实例
        self.failed_models = []  # 存储未成功加载或实例化的模型名称
    def load_models(self):
        """
        动态加载支持的模型类，并实例化模型对象
        """
        # 动态导入所有支持的模型类
        total_model_list = os.listdir("./model")
        for model in total_model_list:
            if "api" in model and "base" not in model:
                model_name = model.split("_")[0].capitalize()
                model_path = model.split(".")[0]
                execute_command = f"""
from model.{model_path} import {model_name}
self.model_classes["{model_name}"] = {model_name}
                """
                try:
                    exec(execute_command)
                except Exception as e:
                    print(f"Error loading model {model_name}: {e}")


         # 实例化模型对象
        for model_name, model_class in self.model_classes.items():
            try:
                api_keys = getattr(config, f"{model_name.lower()}_api_keys", None)
                if not api_keys:
                    raise ValueError(f"API keys for {model_name} not found in config.")

                model_version = model_class.MOST_RECOMMENDED_MODEL[0]
                # model_version = model_class.SOTA
                model_instance = model_class(api_keys, model_version)
                self.model_instances[model_name] = model_instance
            except Exception as e:
                print(f"Error instantiating model {model_name}: {e}")
                self.failed_models.append(model_name)

        if self.failed_models:
            print(f"Models that failed to load or instantiate: {self.failed_models}")

                # 打印成功实例化的模型列表
        if self.model_instances:
            print("Successfully instantiated models:")
            for model_name in self.model_instances:
                print(f" - {model_name}")
        else:
            print("No models were successfully instantiated.")


    def generate_prompts(self):
        """
        根据任务数据生成 prompts
        :return: 生成的 prompts 列表
        """
        prompts = []

        if self.task == "FormulaClarifier":
            # 从 task 对象中获取基础指令和符号映射
            base_instruction = self.instruction
            confusion_map = self.task_obj.confusion_map

            # 将符号映射格式化为易于阅读的字符串
            confusion_map_str = "\n".join([f'- "{symbol}": "{meaning}"' for symbol, meaning in confusion_map.items()])

            for item in self.data:
                # 获取当前数据项的 xyzmn_mapping
                xyzmn_mapping = item.get("xyzmn_mapping", {})
                # 将变量映射格式化为易于阅读的字符串
                xyzmn_mapping_str = "\n".join(
                    [f'- "{variable}": "{meaning}"' for variable, meaning in xyzmn_mapping.items()])

                # 获取需要翻译的原始 prompt 内容
                content_to_translate = item.get("prompt", "")

                # 使用 f-string 构建一个结构清晰、信息丰富的 prompt
                prompt = f"""{base_instruction}

        Here is the context you must use:

        **1. Symbol Meanings:**
        {confusion_map_str}

        **2. Variable Meanings:**
        {xyzmn_mapping_str}

        **Content to Translate:**
        **Do not be limited to simple statements; you may use more complex and obfuscating expressions. The output content is all natural language, rather than translating natural language into mathematical formulas.**
        ---
        {content_to_translate}
        ---
        """
                prompts.append(prompt)
        # 如果 step == "AddContext"，则不包含 JSON 文件中的内容
        elif self.task in ["UselessCondition", "ConfusedCondition", "AddCondition"]:
            prompts = [self.instruction] * len(self.data)  # 仅使用 instruction
        elif self.task in ["MisleadingCondition"]:
            for item in self.data:
                # 提取 xyzmn_mapping 和 abc_mapping
                xyzmn_mapping = item.get("xyzmn_mapping", {})
                abc_mapping = item.get("abc_mapping", {})

                # 将映射转换为字符串格式，例如： "x: 苹果, y: 橘子, ..."
                xyzmn_str = ", ".join([f"{value}" for value in xyzmn_mapping.values()])
                abc_str = ", ".join([f"{value}" for value in abc_mapping.values()])
                # 直接读取 unmapped_entities
                unmapped_entities = item.get("unmapped_entities", [])
                # 将未映射的实体转换为字符串
                unmapped_str = ", ".join(unmapped_entities)

                # 插入映射到指令中
                prompt = f"{self.instruction}\n"  # 基础指令
                prompt += f"题目相关的实体：{xyzmn_str}\n"  # 插入 xyzmn_mapping
                prompt += f"题目中不存在但是相同主题的实体：{abc_str}\n"  # 插入 abc_mapping
                prompt += f"未映射的实体：{unmapped_str}\n"  # 插入未映射实体
                # prompt += f"{item['prompt']}"  # 加入数据中的 prompt
                prompts.append(prompt)
        else:
            for item in self.data:
                prompt = f"{self.instruction}\n{item['prompt']}"
                prompts.append(prompt)
        return prompts

    def _process_chunk(self, model_instance, data_chunk, prompts_chunk):
        """
        处理单个数据块：调用API并返回处理后的数据和token统计。
        :param model_instance: 要使用的模型实例。
        :param data_chunk: 当前要处理的数据项列表。
        :param prompts_chunk: 对应的提示列表。
        :return: 一个元组 (processed_chunk, prompt_tokens, completion_tokens, successful_calls)
        """
        processed_chunk = []
        prompt_tokens = 0
        completion_tokens = 0
        successful_calls = 0

        try:
            results = generation_result(model_instance, prompts_chunk)
            for i, item in enumerate(data_chunk):
                status, text_response, full_json_response = results[i]

                if status == "success":
                    usage_data = full_json_response.get('usage', {})
                    prompt_tokens += usage_data.get('prompt_tokens', 0)
                    completion_tokens += usage_data.get('completion_tokens', 0)
                    successful_calls += 1

                processed_item = {
                    **item,
                    "response": text_response,
                }
                processed_chunk.append(processed_item)

        except Exception as e:
            # 如果 generation_result 内部出错，为这个块的所有项记录错误
            print(f"Error processing a chunk: {e}")
            for item in data_chunk:
                processed_item = {
                    **item,
                    "response": f"Error: Failed to process chunk due to {e}",
                }
                processed_chunk.append(processed_item)

        return processed_chunk, prompt_tokens, completion_tokens, successful_calls

    # ^^^^ 新的辅助函数到此结束 ^^^^

    def run_inference(self, model_name, step):
        model_instance = self.model_instances.get(model_name)
        if not model_instance:
            print(f"Model {model_name} not instantiated")
            return

        print(f"Running inference for model: {model_name}")
        # 1. 初始化汇总变量
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_successful_calls = 0
        all_processed_data = []
        # 定义并行任务数
        NUM_WORKERS = 15

        # 2. 将数据和提示分割成 N 个块
        # 计算每个块的大致大小
        chunk_size = len(self.data) // NUM_WORKERS
        if len(self.data) % NUM_WORKERS != 0:
            chunk_size += 1  # 确保所有项目都被覆盖

        data_chunks = [self.data[i:i + chunk_size] for i in range(0, len(self.data), chunk_size)]
        prompts_chunks = [self.prompts[i:i + chunk_size] for i in range(0, len(self.prompts), chunk_size)]

        FUTURE_TIMEOUT = 310
        # 3. 创建线程池并提交任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            # 提交任务，每个任务处理一个数据块
            future_to_chunk = {
                executor.submit(self._process_chunk, model_instance, data_chunks[i], prompts_chunks[i]): i for i in
                range(len(data_chunks))}

            print(f"Dispatched {len(data_chunks)} chunks to {NUM_WORKERS} workers.")

            # 4. 收集并汇总结果
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk_index = future_to_chunk[future]
                try:
                    full_response_object = future.result(timeout=FUTURE_TIMEOUT)
                    # 从 _process_chunk 的返回中解包
                    processed_chunk, prompt_tokens, completion_tokens, successful_calls = future.result()

                    all_processed_data.extend(processed_chunk)
                    total_prompt_tokens += prompt_tokens
                    total_completion_tokens += completion_tokens
                    total_successful_calls += successful_calls
                    print(f"Chunk {chunk_index + 1}/{len(data_chunks)} completed.")

                except Exception as exc:
                    print(f'Chunk {chunk_index} generated an exception: {exc}')


        processed_new_data = structure_response_into_data(
            all_processed_data,
            self.input_path,
            separator="#",
            field="prompt",
            task_name=self.task
        )


        # 3. 定义主输出文件的路径
        output_file = os.path.join(self.output_path, f"{step}.json")

        # 4. 从主输出文件中，读取之前已经成功的项目
        #    我们复用之前定义的 filter_failed_items 函数，它能同时返回成功和失败的列表
        _, successful_items = filter_failed_items(output_file)
        if successful_items is None:
            successful_items = []  # 如果文件不存在（即第一次运行），则成功列表为空

        # 5. 将【已经成功的旧项目】和【本轮新处理好的项目】合并成一个完整的列表
        final_output_data = successful_items + processed_new_data

        if final_output_data:  # 确保列表不为空
            # 使用更健壮的自然排序，以确保ID排序的准确性
            def sort_key(item):
                item_id = item.get('id', '0_0')
                try:
                    # 尝试按 "数字_数字" 格式解析
                    part1, part2 = map(int, str(item_id).split('_'))
                    return (part1, part2)
                except (ValueError, TypeError):
                    # 如果失败，尝试按单个数字解析
                    try:
                        return (int(item_id), 0)
                    except (ValueError, TypeError):
                        # 如果再次失败，则排在最后
                        return (float('inf'), float('inf'))

            final_output_data = sorted(final_output_data, key=sort_key)
        # ^^^^ 添加结束 ^^^^

        # 6. 将合并后的完整数据写入文件
        model_name_SOTA = model_instance.MOST_RECOMMENDED_MODEL[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_folder_path = self.output_path

        if not os.path.exists(task_folder_path):
            os.makedirs(task_folder_path)

        output_file1 = os.path.join(task_folder_path, f"{step}_{timestamp}.json")

        # 将最终的、完整的数据写入主输出文件和带时间戳的备份文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output_data, f, ensure_ascii=False, indent=4)

        with open(output_file1, 'w', encoding='utf-8') as f:
            json.dump(final_output_data, f, ensure_ascii=False, indent=4)

        print(f"Model {model_name_SOTA} inference completed successfully for this batch.")
        print(f"Output file '{output_file}' now contains {len(final_output_data)} total items.")
        print("\n--- 本次运行Token使用总计 ---")
        print(f"成功的API调用次数: {total_successful_calls}")
        print(f"总输入 Tokens (Prompt): {total_prompt_tokens}")
        print(f"总输出 Tokens (Completion): {total_completion_tokens}")
        print(f"总消耗 Tokens: {total_prompt_tokens + total_completion_tokens}")
        print("---------------------------------\n")
        return

    def run_inference_sequential(self):
        """
        执行所有模型的推理任务
        """
        # 打印成功实例化的模型列表
        if self.model_instances:
            print("Successfully instantiated models:")
            for model_name in self.model_instances:
                print(f" - {model_name}")
        else:
            print("No models were successfully instantiated.")
            return

        # 生成 prompts，只做一次
        self.prompts=self.generate_prompts()

        # 逐个模型执行推理任务
        for model_name in self.model_instances:
            self.run_inference(model_name)

    def run_inference_on_models(self, model_names, step):
        """
        根据传入的模型名称列表，依次执行推理任务
        :param model_names: 模型名称列表
        """
        # 生成 prompts，只做一次
        self.prompts=self.generate_prompts()
        for model_name in model_names:
            if model_name in self.model_instances:
                print(f"Model {model_name} found. Running inference...")
                self.run_inference(model_name, step)
            else:
                print(f"Model {model_name} not found in instantiated models.")


class Evaluator:
    def __init__(self, output_folder, task, output_path, answer_file=None, eval_mode=False, model_list=None):
        """
        初始化 Evaluator 类
        :param output_folder: 需要评估的输出文件所在的文件夹路径
        :param answer_file: 存放标准答案的 JSON 文件路径
        :param task: 任务名称，用于指定加载哪个评估脚本
        :param output_path: 评估结果的保存路径
        :param eval_mode: 是否为评测模式
        :param model_list: 评测使用的模型列表
        """
        self.output_folder = output_folder
        self.answer_file = answer_file
        self.task = task
        self.output_path = output_path
        self.evaluation_script = None
        self.eval_mode = eval_mode
        self.model_list = model_list
        self.model_instances = {}
        self.special_dataset_tags = ["GSM8K"]

        # 如果是评测模式，加载模型
        if self.eval_mode:
            self._load_models_for_evaluation()

    def _load_models_for_evaluation(self):
        """
        为评测模式加载模型，会加载所有推荐的模型版本
        """
        # 动态导入所有支持的模型类
        total_model_list = os.listdir("./model")
        model_classes = {}

        for model in total_model_list:
            if "api" in model and "base" not in model:
                model_name = model.split("_")[0].capitalize()
                model_path = model.split(".")[0]
                execute_command = f"""
from model.{model_path} import {model_name}
model_classes["{model_name}"] = {model_name}
                """
                try:
                    exec(execute_command)
                except Exception as e:
                    print(f"Error loading model {model_name}: {e}")

        # 【主要修改点】实例化模型对象，为每个推荐版本都创建实例
        for model_class_name in self.model_list:
            if model_class_name in model_classes:
                self.model_instances[model_class_name] = {}  # 创建子字典
                try:
                    api_keys = getattr(config, f"{model_class_name.lower()}_api_keys", None)
                    if not api_keys:
                        raise ValueError(f"API keys for {model_class_name} not found in config.")

                    model_class = model_classes[model_class_name]
                    if not hasattr(model_class, 'EVALUATION_MODELS'):
                        print(f"Warning: Model class {model_class_name} does not have an 'EVALUATION_MODELS' list. Skipping for evaluation.")
                        continue
                    # 遍历所有推荐模型
                    for model_version in model_class.EVALUATION_MODELS:
                        model_instance = model_class(api_keys, model_version)
                        self.model_instances[model_class_name][model_version] = model_instance
                        print(f"Successfully loaded model for evaluation: {model_class_name} - {model_version}")

                except Exception as e:
                    print(f"Error instantiating model {model_class_name} for evaluation: {e}")
            else:
                print(f"Model {model_class_name} not found in available models")

    def _load_evaluation_script(self):
        """
        动态加载评估脚本
        """
        script_path = f"./Evaluator/{self.task}_evaluator.py"
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"评估脚本 {script_path} 未找到")

        spec = importlib.util.spec_from_file_location(f"{self.task}_evaluator", script_path)
        self.evaluation_script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.evaluation_script)

    def _save_results(self, evaluation_results, model_version_name, task):
        """
        保存评估结果到以模型名命名的专属文件夹中
        """

        # --- 新增逻辑：动态生成文件名后缀 ---
        filename_suffix = ""
        # 遍历我们在 __init__ 中定义的特殊数据集标签列表
        for tag in self.special_dataset_tags:
            # 检查输入文件路径(self.answer_file)是否包含该标签
            if tag in self.answer_file:
                filename_suffix = f"_{tag}"
                break  # 找到第一个匹配的标签后就停止查找


        model_specific_dir = os.path.join(self.output_path, model_version_name)

        # 2. 【主要修改点】确保这个模型专用的目录存在，如果不存在就创建它
        os.makedirs(model_specific_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if filename_suffix == '':
            output_file_path = os.path.join(model_specific_dir, f"{model_version_name}_evaluation_results_{timestamp}.json")
            output_file_path1 = os.path.join(model_specific_dir, f"evaluation_results.json")
        else:
            output_file_path = os.path.join(model_specific_dir, f"{model_version_name}_evaluation_results{filename_suffix}_{timestamp}.json")
            output_file_path1 = os.path.join(model_specific_dir, f"evaluation_results{filename_suffix}.json")


        # 保存文件的逻辑保持不变
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation_results, f, ensure_ascii=False, indent=4)
        with open(output_file_path1, 'w', encoding='utf-8') as f:
            json.dump(evaluation_results, f, ensure_ascii=False, indent=4)

        print(f"评估结果已保存到: {output_file_path1}")

    def run_model_evaluation(self, model_instance, data):
        """
        使用指定模型实例对数据进行评测，并完整透传原始数据。
        """
        prompts = [item["prompt"] for item in data['problems']]
        total_problems = len(prompts)
        print(f"  > 找到 {total_problems} 道题目需要评测。")
        print(f"  > 正在将所有提示发送至模型进行生成...")

        results = generation_result(model_instance, prompts)
        print(f"  > 已收到 {len(results)} 个回复。正在处理结果...")

        evaluation_results = []
        for i, item in enumerate(data['problems']):
            # 【核心修改】
            # 1. 使用字典解包 `**item` 来复制原始 item 的所有字段，实现数据透传。
            # 2. 然后添加或覆盖 `model_response` 字段。
            result = {
                **item,  # <-- 这一行是关键，它会复制 item 中的所有键值对
                "model_response": results[i][1]
            }
            evaluation_results.append(result)

        return evaluation_results

    def evaluate(self):
        """
        执行评测流程，包含失败重试机制。
        """
        if not self.eval_mode:
            # 原评估逻辑 (非eval模式保持不变)
            # ... (这部分代码保持原样即可)
            evaluation_results = {}
            for output_file in os.listdir(self.output_folder):
                if output_file.endswith('.json') and '_' not in output_file:
                    output_file_path = os.path.join(self.output_folder, output_file)
                    with open(output_file_path, 'r', encoding='utf-8') as f:
                        model_output = json.load(f)

                    evaluator_instance = self.evaluation_script.Evaluator(output_file_path, self.answer_file)
                    evaluation_result = evaluator_instance.evaluate()
                    evaluation_results[output_file] = evaluation_result
            return evaluation_results
        else:
            # --- 新的、带重试功能的评测逻辑 ---
            eval_input_file = self.answer_file
            if not os.path.exists(eval_input_file):
                raise FileNotFoundError(f"指定的评测输入文件未找到: {eval_input_file}")

            with open(eval_input_file, 'r', encoding='utf-8') as f:
                loaded_json = json.load(f)

            if isinstance(loaded_json, list):
                # 如果文件内容直接是一个列表，就手动将它包装成我们需要的字典格式
                initial_data = {'problems': loaded_json}
            else:
                # 否则，我们假定它已经是正确的字典格式了
                initial_data = loaded_json
            if 'problems' in initial_data and isinstance(initial_data['problems'], list):
                total_num_problems = len(initial_data['problems'])
                print(f"原始数据总共有 {total_num_problems} 条。")
                sample_count = 50

                # 确保样本数量不超过数据集的总数
                if total_num_problems > sample_count:
                    random.seed(42)  # 42是一个常用的惯例，您也可以换成任何其他整数
                    # 使用 random.sample 进行随机采样
                    initial_data['problems'] = random.sample(initial_data['problems'], sample_count)
                    print(f"已从数据集中随机选择 {len(initial_data['problems'])} 条数据用于本次评测。")
                else:
                    # 如果总数不足100，则使用全部数据
                    print(f"数据集总数不足{sample_count}条，将使用全部 {total_num_problems} 条数据进行评测。")
            else:
                print("警告：无法在加载的数据中找到 'problems' 列表，将继续处理全部数据。")
            # 对每个加载的模型版本运行评测
            for model_class_name, model_versions in self.model_instances.items():
                print(f"--- 开始处理模型族: {model_class_name} ---")
                for model_version_name, model_instance in model_versions.items():
                    print(f"\n>>> 正在评测模型: {model_version_name}")

                    # 0. 确定当前模型对应的输出文件路径
                    # (这部分逻辑来自 _save_results 方法，我们需要在这里先确定路径)
                    filename_suffix = ""
                    for tag in self.special_dataset_tags:
                        if tag in self.answer_file:
                            filename_suffix = f"_{tag}"
                            break
                    model_specific_dir = os.path.join(self.output_path, model_version_name)
                    os.makedirs(model_specific_dir, exist_ok=True)
                    output_file_path = os.path.join(model_specific_dir, f"evaluation_results{filename_suffix}.json")

                    # --- 在循环开始前，清空旧的输出文件 (和你之前的要求一致) ---
                    if os.path.exists(output_file_path):
                        os.remove(output_file_path)
                        print(f"已删除旧的评测结果文件: {output_file_path}")

                    # 1. 为当前模型设置重试循环
                    max_retries = 3
                    retry_count = 0
                    data_to_process = initial_data  # 第一次运行时处理所有数据

                    while retry_count < max_retries:
                        # 检查是否还有需要处理的数据
                        if not data_to_process or not data_to_process.get('problems'):
                            print("本轮没有需要评测的数据。")
                            break

                        print(f"--- 第 {retry_count + 1} 轮尝试：需要评测 {len(data_to_process['problems'])} 个项目 ---")

                        # 2. 执行模型评测（只对需要处理的数据）
                        newly_processed_results = self.run_model_evaluation(model_instance, data_to_process)

                        # 3. 合并结果并保存
                        # 读取已有的成功结果
                        _, successful_items = filter_failed_items(output_file_path, response_key="model_response")
                        if successful_items is None:
                            successful_items = []

                        # 合并新旧结果
                        final_results = successful_items + newly_processed_results

                        # 根据id对最终结果进行排序
                        # 根据id对最终结果进行排序
                        if final_results:  # 确保列表不为空
                            # 使用我们之前定义的、更健壮的自然排序键
                            def sort_key(item):
                                item_id = item.get('id', '0_0')
                                try:
                                    # 尝试按 "数字_数字" 格式解析
                                    part1, part2 = map(int, str(item_id).split('_'))
                                    return (part1, part2)
                                except (ValueError, TypeError):
                                    # 如果失败，尝试按单个数字解析
                                    try:
                                        return (int(item_id), 0)
                                    except (ValueError, TypeError):
                                        # 如果再次失败，则排在最后
                                        return (float('inf'), float('inf'))

                            final_results = sorted(final_results, key=sort_key)

                        # 保存完整结果
                        if final_results:
                            self._save_results(final_results, model_version_name, self.task)

                        # 4. 检查失败项并准备下一轮
                        failed_items, _ = filter_failed_items(output_file_path, response_key="model_response")

                        if not failed_items:
                            print(f"🎉 模型 {model_version_name} 所有评测任务成功完成！")
                            break

                        print(f"检测到 {len(failed_items)} 个失败的项目，准备为模型 {model_version_name} 重试。")

                        # 更新下一轮要处理的数据
                        data_to_process = {'problems': failed_items}
                        retry_count += 1

                        if retry_count >= max_retries:
                            print(f"达到最大重试次数。模型 {model_version_name} 仍有 {len(failed_items)} 个项目失败。")

            return {"status": "所有模型的评测已完成或达到最大重试次数"}


def filter_failed_items(output_filepath, response_key="response", error_keywords=["retryerro"]):
    """
    读取输出的JSON文件，筛选出失败和成功的数据项。
    :param output_filepath: 要检查的输出文件路径。
    :param response_key: 包含模型响应的字段名（例如 "response" 或 "model_response"）。
    :param error_keywords: 判断为失败的响应中包含的关键词列表。
    :return: 一个元组，包含两个列表 (failed_items, successful_items)。
    """
    if not os.path.exists(output_filepath):
        return None, None

    try:
        with open(output_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None, None

    failed_items = []
    successful_items = []

    for item in data:
        # 使用传入的 response_key 来获取内容
        response = item.get(response_key, "").lower()
        is_failed = False
        if not response:
            is_failed = True
        else:
            for keyword in error_keywords:
                if keyword in response:
                    is_failed = True
                    break

        if is_failed:
            failed_items.append(item)
        else:
            successful_items.append(item)

    return failed_items, successful_items

def run(input_path, output_path, task_name, model_list=None, sample_size=-1, step="UselessCondition", eval_mode=False):
    if eval_mode:
        # 评测模式
        print("Running in evaluation mode...")
        evaluator = Evaluator(
            output_folder=os.path.dirname(input_path),
            task=task_name,
            output_path=output_path,
            answer_file=input_path,
            eval_mode=True,
            model_list=model_list
        )
        evaluator.evaluate()
        # 在 run 函数的 else 块中
    else:
        # 正常推理模式
        max_retries = 10
        retry_count = 0

        output_file_path = os.path.join(output_path, f"{step}.json")
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
            print(f"已删除旧的目标文件: {output_file_path}")

        # 初始要处理的数据，就是输入文件的全部数据
        loader = DatasetLoader(input_path, sample_size)
        loader.load_data()
        data_to_process = loader.get_data()

        while retry_count < max_retries:
            print(f"\n--- 开始第 {retry_count + 1} 轮尝试 ---")

            if not data_to_process:
                print("没有需要处理的数据，流程结束。")
                break

            print(f"本轮需要处理 {len(data_to_process)} 个项目。")

            # 核心推理流程保持不变，但使用 data_to_process 作为输入
            task = Task(task_name)

            # 注意这里，我们将 data_to_process 传递给 Inferrence
            inference = Inferrence(data_to_process, task, input_path, output_path, task_name) # <--- 修改点
            inference.load_models()

            if model_list is None:
                # 这个函数我们暂时还没动，如果使用需要做类似修改
                inference.run_inference_sequential()
            else:
                inference.run_inference_on_models(model_list, step)

            # --- 检查与准备下一轮 ---
            failed_items, successful_items_from_file = filter_failed_items(output_file_path)

            if not failed_items:
                print("🎉 所有任务成功完成！")
                break  # 没有失败项，退出循环

            print(f"检测到 {len(failed_items)} 个失败的项目，准备重试。")

            # 准备下一轮要处理的数据
            data_to_process = failed_items

            retry_count += 1
            if retry_count == max_retries:
                print(f"达到最大重试次数 ({max_retries})。仍有 {len(failed_items)} 个项目失败。")

def main():
    parser = argparse.ArgumentParser(description="Run LLM evaluation pipeline.")

    parser.add_argument("--input_path", type=str, default=None, help="The path to the input dataset.")
    parser.add_argument("--output_path", type=str, default=None, help="The path to save the output results.")
    parser.add_argument("--task_name", type=str, default=None, help="The name of the task to be evaluated.")
    parser.add_argument("--model_list", type=str, nargs='*', default=None, help="List of models to run inference on.")  # 使用 nargs='*' 接收可选的多个模型名称列表
    parser.add_argument("--sample_size", type=int, default=-1, help="The number of sample to be evaluated.")  # 随机选择数据集中的部分样本进行评测，默认全部评测
    parser.add_argument("--step", type=str, default=None, help="This choose the step of the frame.")
    parser.add_argument("--eval", action="store_true", default=False, help="Run in evaluation mode.")
    args = parser.parse_args()

    if args.eval:
        if args.input_path is None:
            args.input_path = "./dataset/9_CombinedProblems/CombinedProblems.json"
        if args.output_path is None:
            args.output_path = "./evaluation_results"
        args.task_name = "Evaluate"
        if args.model_list is None:
            # 测试（免费api）
            # args.model_list = ["Llama"]
            # 完整
            # args.model_list = ["Doubao"]
            # args.model_list = ["Qwen"]
            args.model_list = ["Openai", "Qwen", "Moonshot", "Gemini", "Deepseek"]
            # args.model_list = ["Openai", "Qwen", "Gemini", "Deepseek"]
            # args.model_list = ["Qwen", "Moonshot", "Deepseek"]
            # args.model_list = ["Moonshot"]
            # args.model_list = ["Moonshot"]
            # args.model_list = ["Moonshot"]
            # args.model_list = ["Qwen", "Zhipu", "Doubao", "Deepseek"]
            # args.model_list = ["Qwen", "Llama", "Zhipu", "Doubao", "Deepseek"]

    if args.step == "UselessCondition":# 产出的文件名称
        if args.input_path is None:
            args.input_path = "./dataset/0_InitialData/InitialData.json"
        if args.output_path is None:
            args.output_path = "./dataset/1_UselessCondition"
        args.task_name = "UselessCondition"# 读取的文件名称
        if args.model_list is None:
            args.model_list = ["Openai"]

    elif args.step == "ConfusedCondition":
        if args.input_path is None:
            args.input_path = "./dataset/1_UselessCondition/UselessCondition.json"
        if args.output_path is None:
            args.output_path = "./dataset/2_ConfusedCondition"
        args.task_name = "ConfusedCondition"
        if args.model_list is None:
            args.model_list = ["Openai"]

    elif args.step == "FormulaClarifier":
        if args.input_path is None:
            args.input_path = "./dataset/3_Translated/Translated.json"
        if args.output_path is None:
            args.output_path = "./dataset/4_FormulaClarifier"
        args.task_name = "FormulaClarifier"
        if args.model_list is None:
            args.model_list = ["Deepseek"]

    elif args.step == "MisleadingCondition":
        if args.input_path is None:
            args.input_path = "./dataset/4_FormulaClarifier/FormulaClarifier.json"
        if args.output_path is None:
            args.output_path = "./dataset/5_MisleadingCondition"
        args.task_name = "MisleadingCondition"
        if args.model_list is None:
            args.model_list = ["Openai"] # Deepseek

    elif args.step == "ContextGen":
        if args.input_path is None:
            args.input_path = "./dataset/5_MisleadingCondition/MisleadingCondition.json"
        if args.output_path is None:
            args.output_path = "./dataset/6_ContextGen"
        args.task_name = "ContextGen"
        if args.model_list is None:
            args.model_list = ["Openai"]

    elif args.step == "AddCondition":
        if args.input_path is None:
            args.input_path = "./dataset/6_ContextGen/ContextGen.json"
        if args.output_path is None:
            args.output_path = "./dataset/7_AddCondition"
        args.task_name = "AddCondition"
        if args.model_list is None:
            args.model_list = ["Openai"]
    else:
        # 默认值或其他情况
        args.task_name = "DefaultTask"
    # 变异
    print(args.input_path)

    # Call run function
    run(
        args.input_path,
        args.output_path,
        args.task_name,
        args.model_list,
        args.sample_size,
        args.step,
        eval_mode=args.eval
    )

if __name__ == "__main__":
    main()
