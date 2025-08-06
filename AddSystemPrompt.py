import json
import os

def append_final_question(prompt_text, mapping_dict):
    """
    根据映射字典，在 prompt 末尾添加“求n”的问题。
    :param prompt_text: 现有的 prompt 文本。
    :param mapping_dict: 包含变量'n'和其实体映射的字典。
    :return: 添加了最终问题的新 prompt 文本。
    """
    # 从映射中获取变量 'n' 对应的实体名称，如果找不到则默认为 'n'
    n_entity = mapping_dict.get('n', 'n')
    # 构造要添加的文本
    additional_text = f"Please give me the value of {n_entity}。"
    # 返回拼接后的完整 prompt
    return prompt_text.strip() + '\n' + additional_text


# 文件路径
base_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前脚本所在目录
input_file = os.path.join(base_dir, 'dataset', '7_AddCondition', 'ablation_C', 'AddCondition.json')

# 读取JSON文件
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 遍历列表中的每个字典对象
for item in data:
    prompt = item['prompt']
    # 构造要添加的内容
    additional_text = f"I will demonstrate a mathematics problem for you. Please at the end of your response, please present the answer in the following format: \"The answer to question is \"x\" (replace with numerical values).\""

    # 【新增逻辑】在添加分析结果之前，先更新 prompt 字段
    # 获取当前题目的映射字典
    mapping_dict = item.get("xyzmn_mapping", {})
    # 调用函数，用添加了提问的新 prompt 覆盖旧的 prompt
    item["prompt"] = append_final_question(item.get("prompt", ""), mapping_dict)
    # 更新prompt字段
    item['prompt'] = additional_text + '\n' + prompt + item["prompt"]

# 可选：将修改后的数据保存回文件（或输出处理结果）

# 将修改后的数据覆盖写回原文件
with open(input_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"处理完成，已保存到 {input_file}")