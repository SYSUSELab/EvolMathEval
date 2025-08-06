import os
import json
import re
from fractions import Fraction
import argparse


def append_final_question(prompt_text, mapping_dict):
    """
    根据映射字典，在 prompt 末尾添加“求n”的问题。
    :param prompt_text: 现有的 prompt 文本。
    :param mapping_dict: 包含变量'n'和其实体映射的字典。
    :return: 添加了最终问题的新 prompt 文本。
    """
    # 从映射中获取变量 'n' 对应的中文名称，如果找不到则默认为 'n'
    n_chinese_entity = mapping_dict.get('n', 'n')

    # 构造要添加的文本
    additional_text = f"Please give me the value of {n_chinese_entity}。"

    # 返回拼接后的完整 prompt
    return prompt_text + '\n' + additional_text

# 加载 JSON 数据
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 提取变量值，例如 "n = 3"
def extract_var(answer_text, var_name):
    for segment in answer_text.split('#'):
        segment = segment.strip()
        if segment.startswith(f"{var_name} ="):
            try:
                return int(segment.split('=')[1].strip())
            except ValueError:
                return None
    return None

# 提取 answer 中的第一个数字
def extract_first_number(answer_text):
    for s in answer_text.split():
        if s.lstrip('-').isdigit():
            return int(s)
    return None


# 修改这个函数
def extract_number_after_hash(prompt_text):
    # 找到第一个"#"的位置
    hash_index = prompt_text.find('#')
    if hash_index == -1:
        return None

    # 从第一个"#"之后开始搜索数字
    substring = prompt_text[hash_index + 1:]
    match = re.search(r'-?\d+(?:\.\d+)?', substring)
    if match:
        return float(match.group())
    return None

# 拼接一组题目（前题、后题），插入关系提示，保留后题的原始 answer
def make_combined_item(prev, next_, is_second_evolution, is_formula_clarifier_path):
    prompt1 = prev["prompt"]
    prompt2 = next_["prompt"]

    # 【修改】这是最核心的改动
    # 根据 is_second_evolution 的值来决定从哪里获取 answer
    if is_second_evolution:
        # 如果是 "Second_Evolution" 路径，则从 "answer_next" 获取数据
        answer1 = prev["answer_next"]
        answer2 = next_["answer_next"]
    else:
        # 否则，按照原有的逻辑从 "answer" 获取数据
        answer1 = prev["answer"]
        answer2 = next_["answer"]
    # 【新增】分别获取前后两个题目的映射信息
    prev_item_mapping = prev.get("xyzmn_mapping", {})
    next_item_mapping = next_.get("xyzmn_mapping", {})
    # 【修改】为第一个题目（prev）添加 "求n"
    # prompt1_with_question = append_final_question(prompt1, prev_item_mapping)

    if is_second_evolution:
        prompt1_with_question = prompt1
    else:
        prompt1_with_question = append_final_question(prompt1, prev_item_mapping)


    # 获取 n 和第二道题目中第一个"#"之后的第一个数字
    n_value = extract_var(answer1, 'n')
    to_replace = None
    # ✅ 根据标志位进行判断
    if is_formula_clarifier_path:
        # 如果是特殊情况，调用备用函数，直接找第一个数字
        to_replace = extract_first_number_anywhere(prompt2)
    else:
        # 如果是正常情况，继续使用您原有的函数
        to_replace = extract_number_after_hash(prompt2)

    # 默认关系文本
    relation_text = "1 tiems"

    # 检查 n_value 和 to_replace 是否有效，且 n_value 不为零（避免除法错误）
    if n_value is not None and n_value != 0 and to_replace is not None:
        # 检查是否能整除
        if isinstance(to_replace, float) and not to_replace.is_integer():
            # 如果是小数，为了精确表示，可以先转为字符串或Decimal
            # 这里使用字符串来创建Fraction以保持精度
            frac = Fraction(str(to_replace)) / Fraction(n_value)
            relation_text = f"{frac.numerator}/{frac.denominator} tiems"
        # 如果 to_replace 是整数（或 2.0 这样的浮点数）
        elif to_replace % n_value == 0:
            relation = int(to_replace // n_value)
            relation_text = f"{relation} tiems"
        else:
            # 不能整除的整数
            frac = Fraction(int(to_replace), n_value)
            relation_text = f"{frac.numerator}/{frac.denominator} tiems"

    modified_prompt2 = prompt2
    # 替换第二道题目中第一个"#"之后的第一个数字为 X
    if is_formula_clarifier_path:
        match = re.search(r'-?\d+(?:\.\d+)?', prompt2)
        if match:
            # 从这个match中同时获取要替换的数字和位置信息
            start_pos = match.start()
            end_pos = match.end()
            modified_prompt2 = prompt2[:start_pos] + 'X' + prompt2[end_pos:]
    else:
        hash_index = prompt2.find('#')
        if hash_index != -1:
            substring = prompt2[hash_index + 1:]
            match = re.search(r'-?\d+(?:\.\d+)?', substring)
            if match:
                start_pos = hash_index + 1 + match.start()
                end_pos = hash_index + 1 + match.end()
                modified_prompt2 = prompt2[:start_pos] + 'X' + prompt2[end_pos:]


    # 【新逻辑】根据 is_second_evolution 决定是否为第二个题目添加问题
    if is_second_evolution:
        # 如果是 Second_Evolution 模式，不添加 "求..."
        prompt2_with_question = modified_prompt2
    else:
        # 否则，添加 "求..."
        prompt2_with_question = append_final_question(modified_prompt2, next_item_mapping)

    # 【修改】为修改后的第二个题目（next_）添加 "求n"
    # prompt2_with_question = append_final_question(modified_prompt2, next_item_mapping)

    # 插入提示
    insert_text = f"\nPlease use the answer to the previous question as a baseline. Take {relation_text} its value as the value of X for the next question and continue to solve.\n"
    new_prompt = prompt1_with_question + insert_text + prompt2_with_question

    # 根据 is_second_evolution 模式动态选择引导语
    if is_second_evolution:
        instruction_text = "I will demonstrate a series of combinatorial mathematics problems for you. Please at the end of your response, please present the answer in the following format: \"The answer to question 2 is \"x\", and the final answer is \"y\" (replace with numerical values).\""

    else:
        instruction_text = "I will demonstrate a series of combinatorial mathematics problems for you. Please at the end of your response, please present the answer in the following format: \"The answer to question 1 is \"x\", and the final answer is \"y\" (replace with numerical values).\""

    prompt_with_instruction = prepend_instruction(new_prompt, instruction_text)

    # 3. 【新增】调用新函数，添加最后的“求{n_chinese}”
    final_prompt = prompt_with_instruction

    new_item = prev.copy()

    new_id = f"{prev['id']}_{next_['id']}"
    # --- 结束修改 ---

    # 2. 在这个拷贝上，更新或添加我们需要的字段
    new_item['id'] = new_id                         # 更新ID为能反映顺序的ID
    new_item['prompt'] = final_prompt               # 更新prompt为新生成的交叉prompt
    new_item['answer_prev'] = answer1               # 添加前一个题目的答案
    new_item['answer_next'] = answer2               # 添加后一个题目的答案
    new_item['xyzmn_mapping'] = next_item_mapping   # 更新映射关系为后一个题目的
    # 1. 为 original_prompt, useless_conditions, confused_conditions 创建信息链
    prompt_chain = []
    useless_chain = []
    confused_chain = []

    # -- 处理第一个题目 (prev) --
    # 如果 prev 已经是交叉项，它会有 "_chain" 字段，我们直接继承它的链
    if 'original_prompt_chain' in prev:
        prompt_chain.extend(prev['original_prompt_chain'])
        useless_chain.extend(prev.get('useless_conditions_chain', []))
        confused_chain.extend(prev.get('confused_conditions_chain', []))
    # 否则，prev 是原始项，我们添加它的单个字段
    else:
        prompt_chain.append(prev.get('original_prompt', ''))
        useless_chain.append(prev.get('useless_conditions', ''))
        confused_chain.append(prev.get('confused_conditions', ''))

    # -- 处理第二个题目 (next_) --
    # 逻辑同上
    if 'original_prompt_chain' in next_:
        prompt_chain.extend(next_['original_prompt_chain'])
        useless_chain.extend(next_.get('useless_conditions_chain', []))
        confused_chain.extend(next_.get('confused_conditions_chain', []))
    else:
        prompt_chain.append(next_.get('original_prompt', ''))
        useless_chain.append(next_.get('useless_conditions', ''))
        confused_chain.append(next_.get('confused_conditions', ''))

    # 2. 将构建好的完整信息链保存到 new_item 的新字段中
    new_item['original_prompt_chain'] = prompt_chain
    new_item['useless_conditions_chain'] = useless_chain
    new_item['confused_conditions_chain'] = confused_chain


    new_item['original_prompt'] = next_.get('original_prompt', '')
    new_item['useless_conditions'] = next_.get('useless_conditions', '')
    new_item['confused_conditions'] = next_.get('confused_conditions', '')
    new_item['abc_mapping'] = next_.get('abc_mapping', {})
    new_item['response'] = next_.get('response', '')
    new_item['unmapped_entities'] = next_.get('unmapped_entities', [])

    # 3. 返回这个包含了所有旧字段和新字段的完整 item
    return new_item
# 添加这个新函数
def clean_text(text):
    # 删除所有#
    text = text.replace('#', '')
    # 将换行符替换为空格
    text = text.replace('\n', ' ')
    # 将多个连续空格替换为单个空格
    return re.sub(r'\s+', ' ', text).strip()

def extract_first_number_anywhere(text):
    """
    在整个字符串中查找并返回第一个出现的数字，忽略'#'。
    """
    if not text:
        return None
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if match:
        return float(match.group())
    return None
# 每两个题目配对，顺序生成
def modify_prompts_pairwise(data, is_second_evolution, is_formula_clarifier_path):
    """
    【每个元素只用一次版】
    - 标准模式: (1,2), (3,4) ... 组合，元素不重复使用。
    - Second_Evolution模式: (1,3), (2,4) ... 组合，元素不重复使用。
    """
    modified = []
    n = len(data)

    # --- 标准模式（相邻不重叠配对）---
    # 这个模式本身就符合“每个元素只用一次”的原则，所以保持不变。
    if not is_second_evolution:
        print("执行标准模式：相邻不重叠配对...")
        for i in range(0, n - 1, 2):
            a = data[i]
            b = data[i + 1]
            modified.append(make_combined_item(a, b, is_second_evolution, is_formula_clarifier_path))
            modified.append(make_combined_item(b, a, is_second_evolution, is_formula_clarifier_path))
        if n % 2 != 0:
            last_item = data[-1] # 获取最后一个元素
            print(f"检测到奇数个数据，将最后一个元素 (ID: {last_item['id']}) 直接添加到结果中。")
            modified.append(last_item)
        return modified

    # --- Second_Evolution 模式（间隔不重叠配对）---
    print("执行Second_Evolution模式：每个元素只使用一次...")
    # if n < 3:  # 间隔交叉至少需要3个元素
    #     print("提示: 数据不足3条，无法进行间隔交叉。")
    #     return []

    # 关键机制：创建一个集合，作为“记事本”，记录已被使用的元素的索引
    used_indices = set()

    # 循环只到倒数第三个，因为最后一个和倒数第二个元素无法作为间隔配对的起始点
    for i in range(n - 2):

        # 检查1：如果当前元素i已经被用过，直接跳到下一个
        if i in used_indices:
            continue

        # 确定伙伴的索引
        partner_idx = i + 2

        # 检查2：如果伙伴也已经被用过，那么当前元素i也无法配对，跳到下一个
        if partner_idx in used_indices:
            continue

        # 如果程序能走到这里，说明 i 和 partner_idx 都是可用的，配对成功！
        a = data[i]
        b = data[partner_idx]

        print(f"处理新配对: (索引 {i}, 索引 {partner_idx}) -> (ID: {a['id']}, ID: {b['id']})")

        # 生成 A->B 和 B->A 两个方向的组合
        modified.append(make_combined_item(a, b, is_second_evolution, is_formula_clarifier_path))
        modified.append(make_combined_item(b, a, is_second_evolution, is_formula_clarifier_path))

        # 立刻将这对元素的索引记录到“记事本”中，防止它们被再次使用
        used_indices.add(i)
        used_indices.add(partner_idx)

    print("正在检查是否有未配对的元素...")
    for i in range(n):
        if i not in used_indices:
            remaining_item = data[i]
            print(f"  -> 将剩余元素 (ID: {remaining_item['id']}) 直接添加到结果中。")
            modified.append(remaining_item)

    return modified

# 保存 JSON
# 修改 save_modified_data 函数
def save_modified_data(data, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # 清理所有prompt中的#和换行符
    for item in data:
        item["prompt"] = clean_text(item["prompt"])

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 主流程
# 主流程
def process_file(input_file, output_file):
    data = load_data(input_file)
    # 【新增】检查输入路径是否包含 "Second_Evolution"
    is_second_evolution = "Second_Evolution" in input_file

    # ✅ 【新增】检查路径，创建一个标志位
    is_formula_clarifier_path = "4_FormulaClarifier" in input_file
    print(f"检测到 Second_Evolution 模式: {is_second_evolution}")  # 添加日志方便调试

    # 【修改】将检查结果传递给下一个函数
    modified_data = modify_prompts_pairwise(data, is_second_evolution, is_formula_clarifier_path)

    save_modified_data(modified_data, output_file)
    print(f"✅ 修改后的数据已保存到 {output_file}")

def prepend_instruction(prompt_text, instruction):
    """在给定的 prompt 文本前添加引导语。"""
    return f"{instruction}\n{prompt_text}"

if __name__ == "__main__":
    # 1. 创建一个命令行参数解析器
    parser = argparse.ArgumentParser(description="Combine and modify math problems from a dataset.")

    # 2. 定义程序可以接收的参数，并设置默认值
    #    这样脚本在没有命令行参数时也能使用预设的路径运行
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(base_dir, 'dataset', '7_AddCondition', 'AddCondition.json')
    default_output = os.path.join(base_dir, 'dataset', '8_CrossedCondition', 'CrossedCondition.json')

    parser.add_argument("--input_path", type=str, default=default_input,
                        help="Path to the input JSON file.")

    parser.add_argument("--output_path", type=str, default=default_output,
                        help="Path to save the output JSON file.")

    # 3. 解析用户从命令行输入的参数
    args = parser.parse_args()

    # 4. 调用主处理函数，并将解析到的参数传递进去
    print(f"输入文件: {args.input_path}")
    print(f"输出文件: {args.output_path}")
    process_file(args.input_path, args.output_path)
