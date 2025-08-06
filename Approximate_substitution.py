import json
import random
import re
import argparse


# --- ↓↓↓ 请用这个更强大的新版本，替换掉旧的 find_direct_assignment 函数 ↓↓↓ ---

def find_direct_assignment(equations_list):
    """
    一个更强大的辅助函数，用于寻找可以被直接求解的简单公式。
    它能识别 'm = 8' 以及 '5m = 40' 或 '-2x = 10' 等形式。
    :param equations_list: 传入的公式列表。
    :return: 找到的变量名（如 'm' 或 'x'），如果找不到则返回 None。
    """
    for eq in equations_list:
        parts = eq.split('=', 1)
        if len(parts) == 2:
            left, right = parts[0].strip(), parts[1].strip()

            try:
                # 步骤1：确保公式右边是一个有效的数值
                float(right)

                # 步骤2：找出公式左边所有的变量名
                variables_on_left = re.findall(r'[a-zA-Z]+', left)

                # 步骤3：如果左边有且仅有一个独特的变量名，我们就找到了！
                if len(set(variables_on_left)) == 1:
                    return variables_on_left[0]  # 返回这个变量名

            except ValueError:
                # 如果右边不是数值，或者左边有问题，就跳过这个公式
                continue

    return None


# --- ↑↑↑ 新函数替换结束 ↑↑↑ ---


def modify_variables(equation_part):
    """
    一个辅助函数，用于修改公式字符串中的变量。
    它会随机选择“添加”或“替换”一个变量。
    :param equation_part: 传入的公式字符串（通常是等号左侧的部分）
    :return: 一个元组 (修改后的公式字符串, 操作说明)
    """

    # 随机决定是“添加”还是“替换”
    action = random.choice(["ADD", "REPLACE"])

    # 找出所有现有变量
    all_variables = re.findall(r'[a-zA-Z]+', equation_part)

    if action == "ADD":
        # --- 添加新变量的逻辑 ---
        new_variable_pool = ['x', 'y', 'z', 'm']
        # 找出池子里还未在公式中出现的变量
        available_new_vars = [var for var in new_variable_pool if var not in all_variables]

        if available_new_vars:
            new_variable = random.choice(available_new_vars)
            # 随机决定是用 '+' 还是 '-'
            operator = random.choice(['+', '-'])
            # 构建新的公式部分
            modified_part = f"{equation_part.strip()} {operator} {new_variable}"
            operation_info = f"变量添加 (Variable Addition): 添加了 '{operator} {new_variable}'"
            return modified_part, operation_info

    # --- 如果 action 是 "REPLACE" 或 "ADD" 失败，则执行替换逻辑 ---
    # (这部分逻辑和我们之前的“变量混淆”类似)
    candidate_variables = [var for var in all_variables if var != 'n']

    if candidate_variables:
        variable_to_replace = random.choice(candidate_variables)
        new_variable_pool = ['x', 'y', 'z', 'm']

        if variable_to_replace in new_variable_pool:
            new_variable_pool.remove(variable_to_replace)

        if new_variable_pool:
            new_variable = random.choice(new_variable_pool)
            # 注意：这里的替换可能不完美（比如 'x' 会替换 'max' 里的 'x'），但对于简单公式够用
            modified_part = equation_part.replace(variable_to_replace, new_variable, 1)
            operation_info = f"变量替换 (Variable Replacement): 将 '{variable_to_replace}' 替换为 '{new_variable}'"
            return modified_part, operation_info

    # 如果所有操作都无法进行，则返回原样
    return equation_part, "变量修改: 未执行任何操作"


def process_and_confuse_equations_final(json_content):
    """
    读取包含方程式数据的JSON字符串，对每个条目进行处理。
    代码会自动判断最后一个公式的类型，并采用分层策略进行干扰：
    1. 首选策略：如果找到直接赋值公式 (如 'm=8')，则执行“定向重构”。
    2. 备用策略：如果没有，则执行“随机干扰”（修改变量和数值）。
    最后，将生成的干扰项追加到原prompt末尾。

    Args:
        json_content (str): 包含数据集的JSON格式字符串。
    """
    confusion_map = {
        "≈": "is approximately equal to", ">?": "might be greater than",
        "<?": "might be less than", "~": "is related to",
        "?": "is possibly related to", "=>": "could imply",
        "<-": "could be derived from", "??": "the relationship is unclear",
        "∝": "is possibly proportional to", "<=>?": "is perhaps equivalent to",
        "|?|": "the relationship is ambiguous"
    }
    confusion_symbols = list(confusion_map.keys())

    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        print("错误：提供的字符串不是有效的JSON格式。")
        return None

    for item in data:
        prompt_id = item.get("id")
        prompt_text = item.get("prompt")

        if not prompt_text:
            continue

        equations = prompt_text.split(" # ")
        if not equations:
            continue

        original_last_equation = equations[-1].strip()
        modified_equation = ""
        operation_info = ""

        assignment_var = find_direct_assignment(equations[:-1])

        if assignment_var:
            operation_info = f"模板化重构 (Templated Reconstruction): 使用变量 '{assignment_var}'"
            try:
                # --- 【核心修正】---
                # 1. 寻找定义 assignment_var 的那个原始公式
                defining_equation = ""
                for eq in equations[:-1]:
                    # 检查公式是否以 'x = ...' 或 '5x = ...' 的形式开始
                    if re.match(r'^-?\s*(\d*\.?\d*\s*)?' + re.escape(assignment_var) + r'\b', eq.strip()):
                         defining_equation = eq
                         break

                if not defining_equation:
                    raise ValueError("未找到定义 'assignment_var' 的公式")

                # 2. 从这个找到的【定义公式】中提取数值
                #    这个公式的右侧保证是数值，因为 find_direct_assignment 已经检查过了
                value_str = defining_equation.split('=', 1)[1].strip()
                original_constant = float(value_str)
                # --- 【修正结束】---

                perturbed_value = original_constant + random.randint(10, 30) * random.choice([-1, 1])
                c_var = random.choice([-3, -2, -1, 1, 2, 3])
                c_n = random.choice([-2, -1, 1, 2])
                templates = [
                    f"{c_var}{assignment_var} + {c_n}n = {{const}}",
                    f"{c_n}n + {c_var}{assignment_var} = {{const}}",
                    f"{assignment_var} = {c_n}n + {{const}}",
                    f"n = {c_var}{assignment_var} + {{const}}",
                ]
                chosen_template = random.choice(templates)
                base_equation = chosen_template.format(const=f"{perturbed_value:.1f}")
                random_symbol = random.choice(confusion_symbols)
                modified_equation = base_equation.replace("=", random_symbol, 1)
                operation_info += f" (使用模板: '{chosen_template.split('=')[0].strip()} = ...')"

            except (ValueError, IndexError, TypeError):
                # 如果上述任何一步失败，则回退
                base_equation, var_op_info = modify_variables(original_last_equation)
                random_symbol = random.choice(confusion_symbols)
                modified_equation = base_equation.replace("=", random_symbol, 1)
                operation_info = f"定向重构失败，回退到随机干扰 ({var_op_info})"
        else:
            # 随机干扰逻辑（保持不变）
            base_equation, var_op_info = modify_variables(original_last_equation)
            try:
                parts = base_equation.split('=', 1)
                left_hand_side = parts[0].strip()
                right_hand_side_str = parts[1].strip()
                original_value = float(right_hand_side_str)
                offset = random.randint(10, 30)
                if random.choice([True, False]):
                    offset *= -1
                perturbed_value = original_value + offset
                random_symbol = random.choice(confusion_symbols)
                modified_equation = f"{left_hand_side} {random_symbol} {perturbed_value:.1f}"
                num_op_info = f"数值扰动: {original_value:.1f} -> {perturbed_value:.1f}"
                operation_info = f"随机干扰 (Random Interference) ({var_op_info}); {num_op_info}"

            except (ValueError, IndexError):
                random_symbol = random.choice(confusion_symbols)
                modified_equation = base_equation.replace("=", random_symbol, 1)
                operation_info = f"随机干扰 (Random Interference) ({var_op_info})"

        new_prompt = f"{prompt_text} # {modified_equation}"
        item['prompt'] = new_prompt

        symbol_used = ""
        # 修正查找符号的逻辑，使其更准确
        for s in confusion_symbols:
            # 检查时在符号前后添加空格，避免误匹配
            if f" {s} " in f" {modified_equation.replace('=', ' = ')} ":
                symbol_used = s
                break
        symbol_explanation = confusion_map.get(symbol_used, "N/A")

        print(f"--- 正在处理 ID: {prompt_id} ---")
        print(f"原始 Prompt (处理前): {prompt_text}")
        print(f"  -> 提取的最后一个公式: {original_last_equation}")
        print(f"  -> 执行的干扰操作: {operation_info}")
        print(f"  -> 使用的模糊符号: '{symbol_used}' (含义: {symbol_explanation})")
        print(f"  => 生成的新干扰条件: {modified_equation}")
        print(f"  ==> 最终新 Prompt: {item['prompt']}\n")

    return data

def main(input_path, output_path):
    """
    脚本的主函数，负责读取、处理和保存数据。
    """
    print(f"--- 开始处理 ---")
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            file_content = f.read()

        # --- ↓↓↓ 修改这两行 ↓↓↓ ---
        # 1. 接收返回的已修改数据
        modified_data = process_and_confuse_equations_final(file_content)

        # 2. 如果成功处理，则将其写入新文件
        if modified_data:
            with open(output_path, 'w', encoding='utf-8') as f_out:
                # 使用 json.dump 保存，indent=4 让格式更美观
                json.dump(modified_data, f_out, ensure_ascii=False, indent=4)
            print(f"--- 处理完成，结果已保存至: {output_path} ---")
        # --- ↑↑↑ 修改结束 ↑↑↑ ---

    except FileNotFoundError:
        print(f"错误：找不到指定的文件 '{input_path}'。请确保文件路径正确。")
    except Exception as e:
        print(f"读取或处理文件时发生错误: {e}")


if __name__ == "__main__":
    # 创建一个参数解析器
    parser = argparse.ArgumentParser(description="处理数学公式，生成带干扰项的新数据集。")

    # 添加 --input 参数，用于指定输入文件路径
    parser.add_argument('-i', '--input', type=str, default='dataset/0_InitialData/step1/InitialData.json',
                        help='输入的原始JSON文件路径 (默认: dataset/0_InitialData/step1/InitialData.json)')

    # 添加 --output 参数，用于指定输出文件路径
    parser.add_argument('-o', '--output', type=str, default='dataset/0_InitialData/InitialData.json',
                        help='处理后用于保存的JSON文件路径 (默认: dataset/0_InitialData/InitialData.json)')
    # 解析命令行传入的参数
    args = parser.parse_args()

    # 使用解析到的参数调用 main 函数
    main(args.input, args.output)