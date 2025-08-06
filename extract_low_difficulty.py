import json
import os
import numpy as np
import argparse  # <-- 添加在这里


# --- ↓↓↓ 请用这个【已修改】的函数完整替换你的旧版本 ↓↓↓ ---

def partition_problems_by_score(input_path, low_score_output_path, high_score_output_path, threshold):
    """
    【新功能-V2.1】根据分数阈值将题目分区，并分别保存到两个文件中。
    【新】无论有无数据，都会创建输出文件。
    """
    print(f"正在读取源文件: {input_path}")
    instructional_text = "I will demonstrate a series of combinatorial mathematics problems for you. Please at the end of your response, please present the answer in the following format: \"The answer to question 1 is \"x\", and the final answer is \"y\" (replace with numerical values).\""

    if not os.path.exists(input_path):
        print(f"错误：输入文件不存在！请检查路径：{input_path}")
        return
    # --- 自动创建目录 ---
    low_score_dir = os.path.dirname(low_score_output_path)
    if low_score_dir and not os.path.exists(low_score_dir):
        os.makedirs(low_score_dir)
        print(f"已自动创建目录: {low_score_dir}")

    high_score_dir = os.path.dirname(high_score_output_path)
    if high_score_dir and not os.path.exists(high_score_dir):
        os.makedirs(high_score_dir)
        print(f"已自动创建目录: {high_score_dir}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_problems = data.get('problems', [])
    if not original_problems:
        print("数据集中没有题目，程序提前退出。")
        # 即使没有题目，也创建空的输出文件
        with open(low_score_output_path, 'w', encoding='utf-8') as f: json.dump([], f)
        with open(high_score_output_path, 'w', encoding='utf-8') as f: json.dump(
            {'dataset_level_stats': {}, 'problems': []}, f)
        return

    # --- 步骤 1 & 2: 收集分数并计算阈值 (保持不变) ---
    print("步骤1: 动态识别并收集所有单项特征分数...")
    feature_scores = {}
    for problem in original_problems:
        analysis = problem.get('difficulty_analysis')
        if not (analysis and isinstance(analysis, dict)): continue
        for category_key, category_value in analysis.items():
            if isinstance(category_value, dict):
                for feature_key, feature_value in category_value.items():
                    if isinstance(feature_value, (int, float)):
                        flat_key = f"{category_key}_{feature_key}"
                        if flat_key not in feature_scores: feature_scores[flat_key] = []
                        feature_scores[flat_key].append(feature_value)
    print(f"成功识别并扁平化了 {len(feature_scores)} 个单项难度特征。")

    print("步骤2: 计算各特征的1%分位数阈值...")
    feature_thresholds = {}
    for key, scores in feature_scores.items():
        if scores:
            feature_thresholds[key] = np.percentile(scores, 1)
        else:
            feature_thresholds[key] = -np.inf
    print(f"计算出的各特征1%分位数阈值如下：\n{json.dumps(feature_thresholds, indent=2)}")

    # --- 步骤 3: 筛选 (保持不变) ---
    print("步骤3: 根据阈值筛选题目...")
    low_difficulty_problems = []
    unmodified_low_difficulty_problems = [] # <-- 在这里添加新列表
    high_difficulty_problems = []
    for problem in original_problems:
        is_low_score_problem = False
        removal_reasons = []
        try:
            analysis = problem['difficulty_analysis']
            combined_score = analysis['combined_difficulty_score']
            if combined_score < threshold:
                is_low_score_problem = True
                removal_reasons.append(f"综合分数({combined_score:.2f})低于阈值({threshold})")
            for flat_key, feature_thresh in feature_thresholds.items():
                category_key, feature_key = flat_key.split('_', 1)
                feature_score = analysis.get(category_key, {}).get(feature_key)
                if isinstance(feature_score, (int, float)) and feature_score < feature_thresh:
                    is_low_score_problem = True
                    reason = f"特征'{flat_key}'分数({feature_score:.2f})在最低的1%内(低于{feature_thresh:.2f})"
                    if reason not in removal_reasons: removal_reasons.append(reason)
            if is_low_score_problem:
                unmodified_low_difficulty_problems.append(problem.copy())
                problem['removal_reasons'] = removal_reasons
                problem['prompt'] = problem['prompt'].replace(instructional_text, '').strip()
                low_difficulty_problems.append(problem)
            else:
                high_difficulty_problems.append(problem)
        except (KeyError, TypeError, AttributeError) as e:
            print(f"警告：处理题目 ID '{problem.get('id', 'N/A')}' 时发生错误 '{e}'，已跳过。")
            continue

    # --- 【核心修改 1: 处理并保存低分数据集】 ---
    # 无论列表是否为空，都执行后续操作
    if not low_difficulty_problems:
        print(f"\n未找到需要筛选的低分题目。")
    else:
        print(f"\n成功找到 {len(low_difficulty_problems)} 道低分题目。")
        reason_counts = {}
        for p in low_difficulty_problems:
            for reason in p.get('removal_reasons', ['未知原因']):
                simple_reason = reason.split('(')[0]
                reason_counts[simple_reason] = reason_counts.get(simple_reason, 0) + 1
        print("移除原因统计：")
        for reason, count in sorted(reason_counts.items()):
            print(f" - {reason}: {count} 次")

    # 定义排序函数
    def sort_key(item):
        item_id = item.get('id', '0_0')
        try:
            part1, part2 = map(int, str(item_id).split('_')); return (part1, part2)
        except (ValueError, TypeError):
            try:
                return (int(item_id), 0)
            except (ValueError, TypeError):
                return (float('inf'), float('inf'))

    # 对可能为空的列表进行排序并写入文件
    sorted_low_difficulty_problems = sorted(low_difficulty_problems, key=sort_key)
    with open(low_score_output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_low_difficulty_problems, f, ensure_ascii=False, indent=2)
    print(f"已将 {len(sorted_low_difficulty_problems)} 道低分题目（纯列表格式）保存至：{low_score_output_path}")
    unmodified_output_path = low_score_output_path.replace('.json', '_unmodified.json')
    # 就像处理另一个列表一样：
    sorted_unmodified_list = sorted(unmodified_low_difficulty_problems, key=sort_key)
    # 3. 使用 with open 和 json.dump 写入文件
    with open(unmodified_output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_unmodified_list, f, ensure_ascii=False, indent=2)

    # --- 【核心修改 2: 处理并保存高分数据集】 ---
    # 无论列表是否为空，都执行后续操作
    if not high_difficulty_problems:
        print(f"\n未找到分数高于或等于 {threshold} 的题目。")
    else:
        print(f"\n剩余 {len(high_difficulty_problems)} 道高分题目。")

    # 为可能为空的列表计算统计数据
    high_scores = [p['difficulty_analysis']['combined_difficulty_score'] for p in high_difficulty_problems]

    # 检查列表是否为空，以避免numpy在空列表上发出警告并返回NaN
    if not high_scores:
        dist_stats = {'mean': 0, 'std_dev': 0, 'min': 0, 'max': 0, 'median': 0}
    else:
        dist_stats = {
            'mean': np.mean(high_scores), 'std_dev': np.std(high_scores),
            'min': np.min(high_scores), 'max': np.max(high_scores), 'median': np.median(high_scores)
        }

    high_score_stats = {
        'source_file': input_path,
        'filter_condition': f"combined_score >= {threshold} AND all individual features > 1st percentile",
        'num_problems_retained': len(high_difficulty_problems),
        'difficulty_distribution': dist_stats
    }
    high_score_output_data = {'dataset_level_stats': high_score_stats, 'problems': high_difficulty_problems}

    with open(high_score_output_path, 'w', encoding='utf-8') as f:
        json.dump(high_score_output_data, f, ensure_ascii=False, indent=2)
    print(f"清洗后的高分题目已保存至：{high_score_output_path}")


# --- ↑↑↑ 替换结束 ↑↑↑ ---

if __name__ == "__main__":
    # 1. 创建一个命令行参数解析器
    parser = argparse.ArgumentParser(
        description="Partition problems from a dataset based on a difficulty score threshold.")

    # 2. 定义程序可以接收的参数，并设置默认值
    base_dir = r"dataset\8_CrossedCondition"
    default_input = os.path.join(base_dir, "CrossedCondition_calculate.json")
    default_low_score_output = os.path.join(base_dir, "Second_Evolution\CrossedCondition_low_difficulty.json")
    default_high_score_output = os.path.join(base_dir, "CrossedCondition_cleaned.json")

    parser.add_argument("--input_path", type=str, default=default_input,
                        help="Path to the input JSON file with calculated scores.")

    parser.add_argument("--low_score_output_path", type=str, default=default_low_score_output,
                        help="Path to save problems with scores lower than the threshold.")

    parser.add_argument("--high_score_output_path", type=str, default=default_high_score_output,
                        help="Path to save problems with scores higher than or equal to the threshold.")

    parser.add_argument("--threshold", type=float, default=-0.5,
                        help="The score threshold for partitioning.")

    # 3. 解析用户从命令行输入的参数
    args = parser.parse_args()

    # 4. 调用主处理函数，并将解析到的参数传递进去
    print(f"输入文件: {args.input_path}")
    print(f"低分输出文件: {args.low_score_output_path}")
    print(f"高分输出文件: {args.high_score_output_path}")
    print(f"难度阈值: {args.threshold}")

    partition_problems_by_score(
        args.input_path,
        args.low_score_output_path,
        args.high_score_output_path,
        args.threshold
    )