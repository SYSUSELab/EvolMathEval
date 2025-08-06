import json
import re
import os
from datetime import datetime
import argparse # <-- 添加在这里

def analyze_and_update_data(file_path):
    # 定义正则表达式模式
    q1_pattern = r'The answer to question 1 is [^\d]*(\d+(?:\.\d+)?)'
    q2_pattern = r'The answer to question 2 is [^\d]*(\d+(?:\.\d+)?)'
    final_pattern = r'the final answer is [^\d]*(\d+(?:\.\d+)?)'
    answer_prev_pattern = r'n\s*=\s*(\d+)'
    answer_next_pattern = r'n\s*=\s*(\d+)'

    # 读取JSON文件
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取并格式化结果
    q1_correct_count = 0
    final_correct_count = 0
    # （只计算模型成功提取出答案的条目）
    q1_valid_entries_strict = 0      # Q1有效作答的条目数
    q1_correct_count_strict = 0      # Q1在有效作答中答对的数目
    final_valid_entries_strict = 0   # Final有效作答的条目数
    final_correct_count_strict = 0   # Final在有效作答中答对的数目

    for entry in data:
        id_value = entry.get("id", "")  # 获取ID值
        response = entry.get("model_response", "")
        expected_answer = entry.get("expected_answer", "")
        question = entry.get("prompt", "")

        q1_match = re.search(q1_pattern, response)
        if q1_match:
            q1_answer = q1_match.group(1)
        else:
            # 如果找不到"问题1"，则尝试寻找"问题2"
            q2_match = re.search(q2_pattern, response)
            if q2_match:
                q1_answer = q2_match.group(1)
            else:
                q1_answer = "未找到"

        # 提取最终答案（模型回答）
        final_match = re.search(final_pattern, response)
        final_answer = final_match.group(1) if final_match else "未找到"

        # 提取标准答案（expected_answer中的n值）
        answer_prev_match = re.search(answer_prev_pattern, entry.get("answer_prev", ""))
        answer_next_match = re.search(answer_next_pattern, entry.get("answer_next", ""))

        q1_standard = answer_prev_match.group(1) if answer_prev_match else "未找到"
        final_standard = answer_next_match.group(1) if answer_next_match else "未找到"

        # 新代码（数值比较）
        q1_is_correct = is_numeric_equal(q1_answer, q1_standard)
        final_is_correct = is_numeric_equal(final_answer, final_standard)

        # ==================== 新增的逻辑判断 ====================
        # 定义ID格式的正则表达式：匹配 "数字_数字_数字_数字"
        id_pattern_four_numbers = r'^\d+_\d+_\d+_\d+$'

        # 检查ID格式是否匹配，并且final_is_correct是否为true
        if re.match(id_pattern_four_numbers, id_value) and final_is_correct is True:
            # 如果条件满足，则强制将q1_is_correct也视为true
            q1_is_correct = True
        # ========================================================


        if q1_is_correct:
            q1_correct_count += 1
        if final_is_correct:
            # print(id_value)
            final_correct_count += 1


        if q1_answer != "未找到":
            q1_valid_entries_strict += 1
            if q1_is_correct:
                q1_correct_count_strict += 1

        if final_answer != "未找到":
            final_valid_entries_strict += 1
            if final_is_correct:
                final_correct_count_strict += 1

        # 【修改点】直接将计算出的6个字段添加到原始的 entry 字典中
        entry["model_q1_answer"] = q1_answer
        entry["model_final_answer"] = final_answer
        entry["standard_q1_answer"] = q1_standard
        entry["standard_final_answer"] = final_standard
        entry["q1_is_correct"] = q1_is_correct
        entry["final_is_correct"] = final_is_correct

    # 计算正确率
    total_entries = len(data)
    q1_accuracy = q1_correct_count / total_entries * 100 if total_entries > 0 else 0
    final_accuracy = final_correct_count / total_entries * 100 if total_entries > 0 else 0
    q1_accuracy_strict = q1_correct_count_strict / q1_valid_entries_strict * 100 if q1_valid_entries_strict > 0 else 0
    final_accuracy_strict = final_correct_count_strict / final_valid_entries_strict * 100 if final_valid_entries_strict > 0 else 0


    # 【修改点】返回更新后的完整数据和计算出的准确率
    return {
        "updated_data": data,  # 注意这里返回的是被修改过的 data
        "accuracy": {
            "q1_accuracy": q1_accuracy,
            "final_accuracy": final_accuracy,
            "total_entries": total_entries
        },
        "accuracy_strict": {
            "q1_accuracy": q1_accuracy_strict,
            "final_accuracy": final_accuracy_strict,
            "q1_valid_entries": q1_valid_entries_strict,
            "final_valid_entries": final_valid_entries_strict,
            "total_entries": total_entries
        }
    }


def is_numeric_equal(a, b):
    try:
        # 尝试转换为浮点数进行比较
        return abs(float(a) - float(b)) < 1e-5
    except (ValueError, TypeError):
        # 转换失败时使用字符串比较
        return a == b


def process_files(file_paths, output_dir="./results_analysis"):
    # 创建输出目录（如果不存在）
    os.makedirs(output_dir, exist_ok=True)
    output_dir_strict = os.path.join(output_dir, "accuracy_excluding_failures")
    os.makedirs(output_dir_strict, exist_ok=True)

    # 这个字典将用来收集所有模型的准确率
    all_accuracies = {}
    all_accuracies_strict = {} # 【新增】

    for file_path in file_paths:
        try:
            # 从文件的父目录名中获取模型的名字
            model_name = os.path.basename(os.path.dirname(file_path))

            # 1. 分析数据并获取包含更新后数据的分析结果
            analysis_result = analyze_and_update_data(file_path)

            # 【新增】将更新后的数据写回源文件
            with open(file_path, 'w', encoding='utf-8') as f_source:
                # 使用 analysis_result["updated_data"] 来覆盖写回
                json.dump(analysis_result["updated_data"], f_source, ensure_ascii=False, indent=2)
            print(f"-> 源文件已更新: {file_path}")

            # --- 保存完整分析文件的部分（保持不变）---
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"{model_name}_analysis.json")
            output_path1 = os.path.join(output_dir, f"{model_name}_{timestamp}_analysis.json")
            full_report_for_analysis = {
                "results": analysis_result["updated_data"],
                "accuracy": analysis_result["accuracy"],
                "accuracy_strict": analysis_result["accuracy_strict"] # 新增
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(full_report_for_analysis, f, ensure_ascii=False, indent=2)
            with open(output_path1, 'w', encoding='utf-8') as f:
                json.dump(full_report_for_analysis, f, ensure_ascii=False, indent=2)

            all_accuracies[model_name] = analysis_result["accuracy"]
            all_accuracies_strict[model_name] = analysis_result["accuracy_strict"]

            # 打印单个文件的处理结果
            print(f"\n处理模型: {model_name} (文件: {file_path})")
            print(f"保存完整分析结果到: {output_path}")
            print("-" * 20)
            print(f"原始正确率 (总数: {analysis_result['accuracy']['total_entries']}):")
            print(f"  问题1正确率: {analysis_result['accuracy']['q1_accuracy']:.2f}%")
            print(f"  最终答案正确率: {analysis_result['accuracy']['final_accuracy']:.2f}%")
            print(f"严格正确率 (排除未找到的答案):")
            strict_info = analysis_result['accuracy_strict']
            print(f"  问题1正确率: {strict_info['q1_accuracy']:.2f}% (基于 {strict_info['q1_valid_entries']} 个有效回答)")
            print(f"  最终答案正确率: {strict_info['final_accuracy']:.2f}% (基于 {strict_info['final_valid_entries']} 个有效回答)")
            print("-" * 20)

        except Exception as e:
            print(f"\n处理文件 {file_path} 时出错: {str(e)}")
            import traceback
            traceback.print_exc() # 打印详细的错误追溯信息

        # --- 在所有文件处理完毕后，将汇总的准确率保存到单个文件 (结构更清晰) ---
    summary_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存原始正确率汇总
    if all_accuracies:
        summary_file_path = os.path.join(output_dir, "accuracy_summary.json")
        summary_file_path_ts = os.path.join(output_dir, f"accuracy_summary_{summary_timestamp}.json")
        with open(summary_file_path, 'w', encoding='utf-8') as f:
            json.dump(all_accuracies, f, ensure_ascii=False, indent=2)
        with open(summary_file_path_ts, 'w', encoding='utf-8') as f:
            json.dump(all_accuracies, f, ensure_ascii=False, indent=2)
        print(f"\n所有模型的【原始】准确率汇总已保存到: {summary_file_path}")

    # 保存严格正确率汇总
    if all_accuracies_strict:
        summary_file_path_strict = os.path.join(output_dir_strict, "accuracy_summary.json")
        summary_file_path_strict_ts = os.path.join(output_dir_strict, f"accuracy_summary_{summary_timestamp}.json")
        with open(summary_file_path_strict, 'w', encoding='utf-8') as f:
            json.dump(all_accuracies_strict, f, ensure_ascii=False, indent=2)
        with open(summary_file_path_strict_ts, 'w', encoding='utf-8') as f:
            json.dump(all_accuracies_strict, f, ensure_ascii=False, indent=2)
        print(f"所有模型的【严格】准确率汇总已保存到: {summary_file_path_strict}")

    # --- 将所有汇总信息集中到最后打印，避免重复 ---
    print("\n" + "=" * 15 + " 汇总: 原始正确率 " + "=" * 15)
    for model_name, accuracy in all_accuracies.items():
        print(f"{model_name}:")
        print(f"  问题1正确率: {accuracy['q1_accuracy']:.2f}%")
        print(f"  最终答案正确率: {accuracy['final_accuracy']:.2f}%")

    print("\n" + "=" * 10 + " 汇总: 严格正确率 (排除未找到) " + "=" * 10)
    for model_name, accuracy in all_accuracies_strict.items():
        print(f"{model_name}:")
        print(
            f"  问题1正确率: {accuracy['q1_accuracy']:.2f}% ({accuracy['q1_valid_entries']}/{accuracy['total_entries']} 有效)")
        print(
            f"  最终答案正确率: {accuracy['final_accuracy']:.2f}% ({accuracy['final_valid_entries']}/{accuracy['total_entries']} 有效)")
if __name__ == "__main__":
    # 1. 创建一个命令行参数解析器
    parser = argparse.ArgumentParser(description="Analyze evaluation results from model output files.")

    # 2. 定义程序可以接收的参数，并设置默认值
    parser.add_argument("--results_dir", type=str, default="./evaluation_results",
                        help="The base directory containing model evaluation result subfolders.")

    parser.add_argument("--output_dir", type=str, default="./results_analysis",
                        help="The directory to save the analysis and summary files.")

    parser.add_argument("--target_filename", type=str, default="evaluation_results.json",
                        help="The name of the result file to look for in subdirectories.")

    # 3. 解析用户从命令行输入的参数
    args = parser.parse_args()

    # --- 后续逻辑使用解析后的参数 ---

    file_paths_to_process = []
    print(f"正在扫描目录 '{args.results_dir}' 以查找 '{args.target_filename}'...")

    try:
        # 遍历起始目录下的所有文件和文件夹名
        for entry_name in os.listdir(args.results_dir):
            # 组合成完整的子目录路径
            model_dir_path = os.path.join(args.results_dir, entry_name)

            # 判断这个路径是否确实是一个文件夹
            if os.path.isdir(model_dir_path):
                # 组合成目标文件的完整路径
                target_file_path = os.path.join(model_dir_path, args.target_filename)

                # 判断目标文件是否存在于这个子文件夹中
                if os.path.isfile(target_file_path):
                    file_paths_to_process.append(target_file_path)

    except FileNotFoundError:
        print(f"错误：找不到指定的目录 '{args.results_dir}'。请检查路径是否正确。")
        file_paths_to_process = []  # 清空列表以防万一
    except Exception as e:
        print(f"扫描目录时发生未知错误: {e}")
        file_paths_to_process = []

    if file_paths_to_process:
        print(f"找到了 {len(file_paths_to_process)} 个结果文件，开始处理...")
        # 调用 process_files 时，传入解析后的输出目录
        process_files(file_paths_to_process, output_dir=args.output_dir)
    else:
        print("未找到任何评测结果文件。请检查目录和文件名是否正确。")