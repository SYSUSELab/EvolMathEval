import re
import random
import json
import os
from pathlib import Path
import argparse


# ==== 1. 读取或建立实体库 ====
def load_entity_library(filepath=None):
    if filepath is None:
        filepath = Path(__file__).resolve().parent / "entity_library.json"

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

def _find_and_split_by_symbol(formula, confusion_map):
    """查找并按第一个找到的特殊符号拆分公式"""
    for symbol in sorted(confusion_map.keys(), key=len, reverse=True):
        if symbol in formula:
            parts = formula.split(symbol, 1)
            return parts[0].strip(), symbol, parts[1].strip()
    return None, None, None
# ==== 2. 抽取所有变量和常数 ====
def extract_all_components(formula):
    # 使用正则表达式匹配所有项（包括变量项和常数项）
    components = re.findall(r'[-+]\s*\d*\.?\d*[a-zA-Z]+|[-+]\s*\d+\.?\d*|\d*\.?\d*[a-zA-Z]+|\d+\.?\d*', formula)
    return [comp for comp in components if comp and not comp.isspace()]


def _format_number(n):
    """一个辅助函数，用于将浮点数转为整数（如果可能）"""
    if n == int(n):
        return str(int(n))
    return str(n)

def process_component(component, mapping):

    clean_component = re.sub(r'\s+', '', component)
    # 处理变量项 (如 2x, -y, +3z)
    if re.search(r'[a-zA-Z]', clean_component): # <-- 改为使用 clean_component
        # 提取系数和变量
        coeff_match = re.match(r'([-+]?\d*\.?\d*)([a-zA-Z])', clean_component) # <-- 改为使用 clean_component
        if coeff_match:
            coeff_str = coeff_match.group(1)
            var = coeff_match.group(2)
            entity = mapping.get(var, var)  # 使用映射或保留原变量

            if coeff_str == '':
                # 如果是第一个项，且没有符号 (例如 "a")，则不带任何操作符
                return f"({entity})"
            elif coeff_str == '+':
                # 如果是正号 (例如 "+b")，明确翻译为 "plus"
                return f"plus ({entity})"
            elif coeff_str == '-':
                return f"minus ({entity})"
            else:
                # 处理带数字的系数，例如 '2x', '-4.5y'
                try:
                    coeff_val = float(coeff_str)
                    # 格式化数字，例如将 4.0 变为 4
                    num_str = _format_number(abs(coeff_val))

                    if coeff_val < 0:
                        # 对于负系数，明确输出 "minus"
                        return f"minus {num_str} times ({entity})"
                    else:  # coeff_val > 0
                        # 如果原始系数字符串以'+'开头(如'+2x')，就加上'plus'
                        # 否则(如'2x')就不加，因为可能是首项
                        prefix = "plus " if coeff_str.startswith('+') else ""
                        return f"{prefix}{num_str} times ({entity})"
                except ValueError:
                    # 如果转换失败（理论上不会），则保留原样
                    return f"{coeff_str} times ({entity})"

    # 处理常数项
    elif re.match(r'[-+]?\d+', clean_component): # <-- 改为使用 clean_component
        return clean_component  # 保留原始常数

    return component  # 未知格式，保留原样


# ==== 4. 特殊符号映射 ====
def replace_confusion_symbols(formula):
    # 定义特殊符号映射关系
    confusion_map = {
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

    # 按符号长度降序排序，确保长符号先被替换
    symbols = sorted(confusion_map.keys(), key=len, reverse=True)

    # 逐个替换符号
    for symbol in symbols:
        formula = formula.replace(symbol, confusion_map[symbol])

    return formula


def process_formula(formula, mapping):
    # 准备好特殊符号的定义
    confusion_map = {
        "≈": "is approximately equal to", ">?": "might be greater than",
        "<?": "might be less than", "~": "is related to", "?": "is possibly related to",
        "=>": "could imply", "<-": "could be derived from", "??": "the relationship is unclear",
        "...": "somehow results in", "∝": "is possibly proportional to", "<=>?": "is perhaps equivalent to"
    }

    # 1. 首先，尝试按特殊符号进行拆分
    left, symbol, right = _find_and_split_by_symbol(formula, confusion_map)

    # 2. 如果找到了特殊符号（即，这是一个关系判断句，而不是等式）
    if symbol:
        # 递归调用 process_formula 来翻译左边和右边的纯数学部分
        translated_left = process_formula(left, mapping)
        translated_right = process_formula(right, mapping)

        # 翻译中间的符号
        translated_symbol = confusion_map[symbol]

        # 组合成最终的句子
        return f"{translated_left} {translated_symbol} {translated_right}"

    # 3. 如果没有找到特殊符号（即，这是一个标准的等式）
    #    我们就使用之前为标准等式优化的逻辑
    components = extract_all_components(formula)
    components.sort(key=len, reverse=True)

    # 临时变量，避免修改传入的 `formula`
    processed_formula_str = formula

    for comp in components:
        if comp.strip().isdigit() or not comp.strip():
            continue
        processed_comp = process_component(comp, mapping)
        pattern = r'(?<!\w)' + re.escape(comp) + r'(?!\w)'
        processed_formula_str, count = re.subn(pattern, processed_comp, processed_formula_str, count=1)

    # 对处理好的等式进行最终清理
    final_formula = processed_formula_str.strip()
    final_formula = final_formula.replace(' + minus ', ' minus ').replace(' - ', ' minus ')
    final_formula = re.sub(r'=\s*-', '= negative ', final_formula)

    if final_formula.startswith('minus '):
        final_formula = 'negative' + final_formula[5:]
    elif final_formula.startswith('-'):
        final_formula = 'negative ' + final_formula[1:]

    return re.sub(r'\s+', ' ', final_formula).strip()


# ==== 6. 主处理函数 ====
def process_translate_file(input_path, output_path):

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entity_library = load_entity_library()
    results = []

    # (请用下面的完整代码块替换您脚本中现有的 for item in data: 循环)

    for item in data:
        # --- 步骤 1-5: 变量提取和映射 (这部分您已完全正确) ---
        original_prompt_str = item.get("prompt", "")
        useless_conditions_str = item.get("useless_conditions", "")
        confused_conditions_str = item.get("confused_conditions", "")
        item["original_prompt"] = original_prompt_str
        string_for_var_extraction = "#".join(
            filter(None, [original_prompt_str, useless_conditions_str, confused_conditions_str]))
        all_formulas_for_vars = [f.strip() for f in string_for_var_extraction.split('#') if f.strip()]
        all_vars = set()
        for formula in all_formulas_for_vars:
            components = extract_all_components(formula)
            for comp in components:
                if re.search(r'[a-zA-Z]', comp):
                    var_match = re.search(r'([a-zA-Z])', comp)
                    if var_match:
                        all_vars.add(var_match.group(1))
        all_vars = list(all_vars)
        theme = random.choice(list(entity_library.keys()))
        entity_pool = random.sample(entity_library[theme], k=min(15, len(entity_library[theme])))
        if len(all_vars) > len(entity_pool):
            print(f"跳过题目 ID {item['id']}：变量数({len(all_vars)}) > 实体池大小({len(entity_pool)})")
            continue
        var_entity_mapping = dict(zip(all_vars, random.sample(entity_pool, len(all_vars))))
        xyzmn_mapping = {var: ent for var, ent in var_entity_mapping.items() if var in 'xyzmnefh'}
        abc_mapping = {var: ent for var, ent in var_entity_mapping.items() if var in 'abc'}

        # --- 步骤 6: 翻译原始 prompt 中的公式 ---
        formulas_to_translate = [f.strip() for f in string_for_var_extraction.split('#') if f.strip()]
        translated_prompts = []

        # 【开始翻译循环】
        for formula in formulas_to_translate:
            try:
                processed_formula = process_formula(formula, var_entity_mapping)
                translated_prompts.append(processed_formula)
            except Exception as e:
                print(f"处理公式失败：{formula}，错误：{e}")
                translated_prompts.append(formula)
        # 【翻译循环结束】

        # --- 步骤 7: 在循环【外部】拼接最终结果并更新 item ---
        # 这个 if 块现在位于正确的缩进级别
        if translated_prompts:

            final_prompt = " # ".join(translated_prompts)

            mapped_entities = set(var_entity_mapping.values())
            all_entities = set(entity_pool)
            unmapped_entities = list(all_entities - mapped_entities)

            item["prompt"] = final_prompt
            item["xyzmn_mapping"] = xyzmn_mapping
            item["abc_mapping"] = abc_mapping
            item["unmapped_entities"] = unmapped_entities

            results.append(item)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 1. 创建一个命令行参数解析器
    parser = argparse.ArgumentParser(description="Translate formulaic prompts into natural language.")

    # 2. 定义程序可以接收的参数
    #    我们为每个参数都设置了 `default` 值，这样即使用户不提供，程序也能正常运行
    base_dir = Path(__file__).resolve().parent
    default_input = base_dir / "dataset/2_ConfusedCondition/ConfusedCondition.json"
    default_output = base_dir / "dataset/3_Translated/Translated.json"

    parser.add_argument("--input_path", type=str, default=default_input,
                        help="Path to the input JSON file.")

    parser.add_argument("--output_path", type=str, default=default_output,
                        help="Path to save the output JSON file.")

    # 3. 解析用户从命令行输入的参数
    args = parser.parse_args()

    # 4. 调用主处理函数，并将解析到的参数（无论是用户输入的还是默认的）传递进去
    print(f"输入文件: {args.input_path}")
    print(f"输出文件: {args.output_path}")
    process_translate_file(args.input_path, args.output_path)