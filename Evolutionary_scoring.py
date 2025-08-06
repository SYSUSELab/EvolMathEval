import json
import re
# 确保你有名为 config.py 的配置文件
import model.config as config
# 这个函数需要被定义，我们将在测试中创建一个模拟（mock）版本
from model.base_model_api import generation_result
import argparse
import os # <--- 添加 os 库，用于文件检查
import concurrent.futures # <--- 添加并发库


def filter_failed_items(filepath):
    """
    读取文件，筛选出失败和成功的数据项。
    失败项：没有 'difficulty_score' 键，或者该键的值不是数字。
    成功项：拥有 'difficulty_score' 键且值为数字。
    :param filepath: 要检查的 JSON 文件路径。
    :return: 一个元组 (failed_items, successful_items)。
    """
    if not os.path.exists(filepath):
        # 如果文件不存在，说明是第一次运行，所有项目都应被处理
        try:
            with open(filepath.replace('.json', '_initial.json'), 'r', encoding='utf-8') as f:
                return json.load(f), []
        except FileNotFoundError:
            # 如果初始文件也不存在，我们需要从一个干净的源头加载
            # 为了简单起见，我们假设 evaluator 会处理这种情况
            return [], []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return [], []  # 如果文件为空或损坏，返回空列表

    failed_items = []
    successful_items = []

    for item in data:
        score = item.get('difficulty_score')
        # 如果'difficulty_score'不存在，或者存在但不是整数或浮点数，则视为失败
        if score is None or not isinstance(score, (int, float)):
            failed_items.append(item)
        else:
            successful_items.append(item)

    return failed_items, successful_items

class Evaluator:
    def __init__(self, file_to_process):
        """
        初始化 Evaluator 类
        :param output_file: 需要评估的输出文件路径
        :param answer_file: 存放标准答案的 JSON 文件路径,此评估没有标准答案
        """
        self.file_path = file_to_process # 将 output_file 重命名为更通用的 file_path
        # ... 类的其他初始化代码保持不变 ...
        self.model_class = {}
        self.model_instance = {}
        self.failed_models = []
        self.prompts = []

        self.model_class = {}  # 存储模型类
        self.model_instance = {}  # 存储模型实例
        self.failed_models = []  # 初始化失败模型列表

        self.prompts = []

        # 只导入和实例化 Openai 模型
        model_name = "Openai"
        # 这里的路径指的是 Python 文件名，例如 'openai_api.py'
        model_path = "openai_api"

        # 动态导入 Openai 模型类
        try:
            execute_command = f"from model.{model_path} import {model_name}\n" \
                              f"self.model_class[\"{model_name}\"] = {model_name}"
            exec(execute_command)
            print(f"成功加载模型类: {model_name}")
        except Exception as e:
            print(f"加载模型 {model_name} 时出错: {e}")

        # 实例化 Openai 模型对象
        try:
            # 假设 config.py 文件中有一个类似这样的变量: openai_api_keys = ["sk-xxxx", "sk-yyyy"]
            api_keys = getattr(config, f"{model_name.lower()}_api_keys", None)
            if not api_keys:
                raise ValueError(f"在 config.py 中未找到 {model_name} 的 API 密钥。")

            # 假设 Openai 类中定义了推荐模型的列表
            model_version = self.model_class[model_name].MOST_RECOMMENDED_MODEL[0]
            self.model_instance = self.model_class[model_name](api_keys, model_version)
            print(f"成功实例化模型: {model_name}，使用版本: {model_version}")
        except Exception as e:
            print(f"实例化模型 {model_name} 时出错: {e}")
            self.failed_models.append(model_name)

    def _process_chunk(self, data_chunk, prompts_chunk):
        """
        处理单个数据块：调用API，处理返回的分数，并返回附带统计信息的结果。
        """
        processed_chunk = []
        prompt_tokens = 0
        completion_tokens = 0
        successful_calls = 0

        # 调用模型API
        results = generation_result(self.model_instance, prompts_chunk)

        for i, item in enumerate(data_chunk):
            if i < len(results):
                status, score_value, full_json_response = results[i]

                if status == "success":
                    usage_data = full_json_response.get('usage', {})
                    prompt_tokens += usage_data.get('prompt_tokens', 0)
                    completion_tokens += usage_data.get('completion_tokens', 0)
                    successful_calls += 1

                # Evaluator 类中的 _process_chunk 方法

                try:
                    # 使用 float() 来正确处理可能带小数的评分
                    final_score = float(score_value)
                except (ValueError, TypeError):
                    final_score = str(score_value)

                # 更新项目字典，但不修改原始的 item
                processed_item = {**item, 'difficulty_score': final_score}
                processed_chunk.append(processed_item)

        return processed_chunk, prompt_tokens, completion_tokens, successful_calls

    def _run_parallel_evaluation(self, items_to_process, prompts):
        """
        使用多线程并行处理所有需要评估的项目。
        """
        all_processed_data = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_successful_calls = 0
        NUM_WORKERS = 20  # 你可以根据需要调整线程数

        # 将数据和提示分割成块
        chunk_size = (len(items_to_process) + NUM_WORKERS - 1) // NUM_WORKERS
        data_chunks = [items_to_process[i:i + chunk_size] for i in range(0, len(items_to_process), chunk_size)]
        prompts_chunks = [prompts[i:i + chunk_size] for i in range(0, len(prompts), chunk_size)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            future_to_chunk = {
                executor.submit(self._process_chunk, data_chunks[i], prompts_chunks[i]): i
                for i in range(len(data_chunks))
            }

            print(f"任务已分发给 {NUM_WORKERS} 个工作线程...")
            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    processed_chunk, p_tokens, c_tokens, s_calls = future.result()
                    all_processed_data.extend(processed_chunk)
                    total_prompt_tokens += p_tokens
                    total_completion_tokens += c_tokens
                    total_successful_calls += s_calls
                except Exception as exc:
                    print(f"一个处理块产生异常: {exc}")

        return all_processed_data, total_prompt_tokens, total_completion_tokens, total_successful_calls

    def evaluate(self):
        """
        评估主流程，包含重试和并行处理机制。
        """
        max_retries = 5
        retry_count = 0

        # 为了防止在重试过程中反复读取和覆盖源文件，我们先做一个备份
        # 如果输出文件已存在，我们假设它就是我们要处理的状态
        if not os.path.exists(self.file_path):
            # 尝试从一个预定义的初始文件加载数据
            initial_file = 'dataset/8_CrossedCondition/CrossedCondition.json'  # 确保这个路径正确
            try:
                with open(initial_file, 'r', encoding='utf-8') as f:
                    initial_data = json.load(f)
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, ensure_ascii=False, indent=4)
                print(f"从 {initial_file} 创建了工作文件 {self.file_path}")
            except FileNotFoundError:
                print(f"错误: 初始文件 {initial_file} 未找到，无法开始处理。")
                return

        while retry_count < max_retries:
            print(f"\n--- 开始第 {retry_count + 1}/{max_retries} 轮尝试 ---")

            # 1. 筛选出需要处理的失败项和已经成功的项目
            items_to_process, successful_items = filter_failed_items(self.file_path)

            if not items_to_process:
                print("🎉 所有项目均已成功处理！流程结束。")
                break

            print(f"找到 {len(items_to_process)} 个需要处理的项目。")

            # 2. 仅为需要处理的项目生成 Prompts
            prompts_to_run = []
            for item in items_to_process:
                question = item.get('prompt', '')
                prompt = (
                    "Rate the cognitive difficulty of the following problem on a scale of 0-10.\n\n"
                    "IMPORTANT: The underlying math is simple. The real difficulty is in the confusing language, irrelevant details, and logical steps. Your score must reflect how hard the text is to understand, NOT how hard the math is.\n\n"
                    "Use this scale:\n"
                    "- 0-3: Language is direct and easy to follow.\n"
                    "- 4-6: Language is complex or contains noise, requiring careful reading.\n"
                    "- 7-10: Language is intentionally confusing, tricky, or hides the core question.\n\n"
                    "Problem:\n"
                    f"<question>{question}</question>\n\n"
                    "Your response must be only a single numerical score. Decimal values (e.g., 4.5, 7.2) are encouraged for finer granularity."
                )
                prompts_to_run.append(prompt)

            # 3. 调用并行调度器执行处理
            (newly_processed_data, p_tokens,
             c_tokens, s_calls) = self._run_parallel_evaluation(items_to_process, prompts_to_run)

            print("\n--- 本轮Token使用统计 ---")
            print(f"成功的API调用次数: {s_calls} / {len(prompts_to_run)}")
            print(f"输入 Tokens: {p_tokens}, 输出 Tokens: {c_tokens}")
            print("--------------------------\n")

            # 4. 合并新处理好的数据和之前已经成功的数据
            final_output_data = successful_items + newly_processed_data

            # 5. (重要) 对合并后的数据按 id 排序，确保文件内容顺序稳定
            if final_output_data:
                def sort_key(item):
                    # 获取ID，如果不存在则使用 '0_0' 作为默认值
                    item_id = item.get('id', '0_0')
                    try:
                        # 分割ID并转换为整数元组，例如 "10_2" -> (10, 2)
                        part1, part2 = map(int, str(item_id).split('_'))
                        return (part1, part2)
                    except (ValueError, TypeError):
                        # 如果ID格式不正确，则返回一个默认值使其排在后面
                        return (float('inf'), float('inf'))

                final_output_data = sorted(final_output_data, key=sort_key)

            # 6. 将完整数据写回文件，为下一轮或最终结果做准备
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(final_output_data, f, ensure_ascii=False, indent=4)

            print(
                f"第 {retry_count + 1} 轮完成，结果已保存。文件 '{self.file_path}' 包含 {len(final_output_data)} 个项目。")

            retry_count += 1
            if retry_count == max_retries:
                remaining_failures, _ = filter_failed_items(self.file_path)
                if remaining_failures:
                    print(f"达到最大重试次数。仍有 {len(remaining_failures)} 个项目处理失败。")
                else:
                    print("🎉 所有项目均已在最后一次尝试中成功处理！")

        print("\n评估流程执行完毕。")


# ==============================================================================
# 用于测试 Evaluator 的主执行代码块
# ==============================================================================
if __name__ == "__main__":
    # 1. 创建一个命令行参数解析器
    parser = argparse.ArgumentParser(description="Add difficulty scores to a dataset using an LLM.")

    # 2. 定义程序可以接收的 --file_path 参数，并设置默认值
    default_file_path = 'dataset/8_CrossedCondition/CrossedCondition.json'
    parser.add_argument("--file_path", type=str, default=default_file_path,
                        help="Path to the JSON file to be processed.")

    # 3. 解析用户从命令行输入的参数
    args = parser.parse_args()

    # 4. 使用解析到的参数创建并实例化 Evaluator
    print("正在初始化评估器...")
    print(f"将要处理的文件: {args.file_path}")
    evaluator = Evaluator(file_to_process=args.file_path) # 使用命令行参数

    # 5. 运行评估
    if not evaluator.failed_models:
        evaluator.evaluate()
    else:
        print("由于模型初始化失败，评估已跳过。")