import json
import re
# 确保你有名为 config.py 的配置文件
import model.config as config
# 这个函数需要被定义，我们将在测试中创建一个模拟（mock）版本
from model.base_model_api import generation_result


class Evaluator:
    def __init__(self, output_file, answer_file):
        """
        初始化 Evaluator 类
        :param output_file: 需要评估的输出文件路径
        :param answer_file: 存放标准答案的 JSON 文件路径,此评估没有标准答案
        """
        self.output_file = output_file

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

    def evaluate(self):
        """
        评估指定的输出文件，并为数据添加难度评分
        """
        self.prompts = []  # 清空或初始化 prompts 列表

        # 读取输出文件
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                model_output = json.load(f)
        except FileNotFoundError:
            print(f"错误: 在路径 {self.output_file} 未找到输出文件")
            return
        except json.JSONDecodeError:
            print(f"错误: 文件 {self.output_file} 不是有效的 JSON 格式。")
            return

        # --- 为方便测试进行的修改 ---
        # 只取前3条数据进行测试
        # model_output_subset = model_output[13:29]
        model_output_subset = model_output

        # 遍历筛选后的数据子集
        for item in model_output_subset:
            question = item.get('prompt')  # 使用 .get() 以防 'prompt' 键不存在
            if not question:
                print("警告: 发现一个项目缺少 'prompt' 键，已跳过。")
                continue

            # 构建 prompt
            prompt = (
                f"判断这道题目的解题难度，给定一个从0到10的分值，10表示最难\n"
                f"<题目>{question}</题目>"
                "注意：你只需回复一个分数，不得有其他内容"
            )
            self.prompts.append(prompt)

        # 使用模型生成的分类结果
        results = generation_result(self.model_instance, self.prompts)

        # 将生成的结果添加到原始 model_output 列表对应项的 'type' 字段中
        # 注意：这只会更新原始列表中的前三项
        # 将生成的结果作为新字段 'difficulty_score' 添加到每一项中
        # 注意：这只会更新原始列表中的前三项
        for i, item in enumerate(model_output_subset):
            if i < len(results):
                # 从模型返回的结果中提取分数（通常在第二个位置）
                score_value = results[i][1]

                # (推荐) 尝试将分数转换为整数，如果失败则保持原样
                try:
                    # 将字符串'8'转换为数字8
                    final_score = int(score_value)
                except (ValueError, TypeError):
                    # 如果模型返回的不是数字（例如返回了一段文字或错误信息），则直接使用原始值
                    final_score = score_value

                # 创建一个名为 'difficulty_score' 的新变量（键）并赋值
                item['difficulty_score'] = final_score
                print(f"  - 已处理第 {i + 1} 项: 添加难度分数 '{final_score}'")

        # 将更新后的 model_output 完整地保存回原始输出文件
        # 这会用部分更新后的列表覆盖原始文件
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(model_output, f, ensure_ascii=False, indent=4)

        print(f"\n评估完成。文件 '{self.output_file}' 已被更新。")
        return


# ==============================================================================
# 用于测试 Evaluator 的主执行代码块
# ==============================================================================
if __name__ == "__main__":
    # 1. 定义文件路径
    #    - output.json 是你的模型输出文件，它将被读取和修改。
    #    - answer.json 在这个场景下不被使用，但 __init__ 方法需要它。
    output_file_path = '../dataset/8_CrossedCondition/CrossedCondition.json'
    answer_file_path = 'answer.json'  # 虚拟文件, 在此逻辑中未使用

    # 2. 创建并实例化 Evaluator
    print("正在初始化评估器...")
    evaluator = Evaluator(output_file=output_file_path, answer_file=answer_file_path)

    # 3. 运行评估 (只会处理前3条)
    if not evaluator.failed_models:  # 仅在模型成功加载后运行
        evaluator.evaluate()
    else:
        print("由于模型初始化失败，评估已跳过。")