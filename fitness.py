import json
import os
from collections import Counter
import math
import spacy
import warnings
import argparse
import re
import numpy as np
from sklearn.preprocessing import StandardScaler
import textstat  # <--- 在这里添加这一行

# --- 核心改进：使用包含词向量的中型模型 ---
# 提示：在运行前，请务必在命令行执行: python -m spacy download zh_core_web_md
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    print("错误：找不到'en_core_web_md'模型。")
    print("请在你的终端或命令行中运行：python -m spacy download zh_core_web_md")
    exit()

# 检查模型是否包含词向量，这是语义相似度的基础
if len(nlp.vocab.vectors) == 0:
    print("警告：你加载的spaCy模型不包含词向量，无法计算语义相似度。")
    print("请确认你已安装并加载 'zh_core_web_md' 或 'zh_core_web_lg'。")
    # 在这里可以选择退出或降级到其他方法
    # exit()


# 1. 信息熵计算 (保留字符熵，新增词语熵)
def calculate_char_level_entropy(text):
    """计算文本的信息熵（字符级别）"""
    if not text:
        return 0.0
    char_counts = Counter(text)
    total_chars = len(text)
    return -sum((count / total_chars) * math.log2(count / total_chars) for count in char_counts.values())


def calculate_word_level_entropy(doc):
    """【新】计算文本的信息熵（词语级别）"""
    words = [token.text for token in doc if not token.is_stop and not token.is_punct]
    if not words:
        return 0.0
    word_counts = Counter(words)
    total_words = len(words)
    return -sum((count / total_words) * math.log2(count / total_words) for count in word_counts.values())


def calculate_word_count(doc):
    """计算文本的单词数"""
    return len([token for token in doc if not token.is_punct])


def calculate_second_highest_similarity(docs):
    """
    【新】计算每个题目在数据集中的第二高相似度得分。
    :param docs: spaCy处理过的文档列表
    :return: 一个列表，包含每个题目的第二高相似度得分
    """
    num_docs = len(docs)
    if num_docs < 3: # 至少需要3个文件才能有“第二高”
        return [0.0] * num_docs

    # 1. 创建一个N x N的矩阵，用于存放所有题目两两之间的相似度
    similarity_matrix = np.zeros((num_docs, num_docs))

    # 2. 填充这个矩阵
    for i in range(num_docs):
        for j in range(i, num_docs):
            score = docs[i].similarity(docs[j])
            similarity_matrix[i, j] = score
            similarity_matrix[j, i] = score

    # 3. 将对角线（自己和自己的相似度）设置为一个非常小的值，确保它不会被选为最高或第二高
    np.fill_diagonal(similarity_matrix, -1.0)

    # 4. 【核心修改】对每一行（代表每一道题），找到该行的第二高的值
    second_highest_scores = []
    for row in similarity_matrix:
        # 对每一行进行排序（从小到大），然后取倒数第二个值。
        # 这就是除自身和最高相似项之外的下一个最相似得分。
        second_highest_scores.append(np.sort(row)[-2])

    return second_highest_scores

# ======================================================================================

# ========================================================================

# <--- 用这个新函数替换被删除的函数
def calculate_readability_en(text):
    return textstat.flesch_kincaid_grade(text)


def get_syntactic_complexity(doc):
    """计算句法复杂度 (最大依存树深度)"""

    def get_depth(token, current_depth):
        if not list(token.children):
            return current_depth
        return max([get_depth(child, current_depth + 1) for child in token.children] + [current_depth])

    max_depth = 0
    for sent in doc.sents:
        if sent.root:
            max_depth = max(max_depth, get_depth(sent.root, 1))
    return max_depth


# B. 数学和逻辑层面
def extract_math_features(text, doc):
    """提取核心的数学/逻辑特征"""
    lang_keywords = {
        'zh': {
            'equation': ['等于', '再加', '减去', '是', '得到', '归零', '差值', '总和', '为'],
            'nonlinear': ['乘以', '除以', '商为', '积为', '平方', '立方'],
            'variable_units': ['倍', '浓度', '花费', '距离', '总价', '路程', '费用', '原液', '颜料', '总额']
        },
        'en': {
            'equation': [
                'equals', 'plus', 'minus', 'is', 'results in', 'difference is',
                'sum is', 'total of', 'add', 'added to', 'subtract', 'less',
                'more than', 'less than', 'increased by', 'decreased by', 'gives',
                'yields', 'makes', 'altogether', 'combined with', 'take away'
            ],

            'nonlinear': [
                'multiplied by', 'divided by', 'product is', 'quotient is',
                'squared', 'cubed', 'times', 'product of', 'per', 'ratio of',
                'percent of', 'power of', 'square root', 'cube root', 'rate of'
            ],

            'variable_units': [
                'concentration', 'cost', 'distance', 'price', 'fee', 'rate',
                'speed', 'time', 'hours', 'minutes', 'seconds', 'amount',
                'height', 'width', 'length', 'area', 'volume', 'weight', 'mass',
                'temperature', 'salary', 'tax', 'discount'
            ]
        }
    }
    lang = nlp.lang
    keywords = lang_keywords.get(lang, lang_keywords['en'])

    sentences = [sent.text.strip() for sent in doc.sents]  # <--- 修改这里
    equation_pattern = '|'.join(keywords['equation'])
    num_equations = sum(1 for sent in sentences if re.search(equation_pattern, sent, re.IGNORECASE))


    variables = set()
    for token in doc:
        if token.pos_ in ['NOUN', 'PROPN'] and token.i + 1 < len(doc):
            next_token_text = doc[token.i + 1].text
            if next_token_text in keywords['variable_units']:
                variables.add(token.text)
    num_variables = len(variables)

    nonlinear_pattern = '|'.join(keywords['nonlinear'])
    non_linear_count = len(re.findall(nonlinear_pattern, text, re.IGNORECASE))

    total_len = len(text)
    if total_len == 0:
        return 0, 0, 0, 0.0

    signal_len = sum(len(sent) for sent in sentences if re.search(equation_pattern, sent))
    noise_ratio = (total_len - signal_len) / total_len if total_len > 0 else 0.0

    return num_equations, num_variables, non_linear_count, noise_ratio


# ================= 请用下面的函数【完全替换】旧的 process_prompts 函数 =================

def process_prompts(input_path, output_path):
    """
    处理JSON文件的主要函数 (最终版：包含所有已定义的、有价值的指标)
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # --- 步骤1: 预处理和计算所有单项指标 ---
    print("步骤1: 预处理和计算所有单项指标...")
    prompts = [item['prompt'] for item in data]
    docs = list(nlp.pipe(prompts))

    second_highest_scores = calculate_second_highest_similarity(docs)

    all_problem_features = []
    for i, item in enumerate(data):
        doc = docs[i]
        prompt_text = item['prompt']

        num_eq, num_var, non_linear, noise = extract_math_features(prompt_text, doc)

        features = {
            'id': item.get('id', i),
            # 【新增】读取裁判模型的打分，如果不存在则默认为5（中等难度）
            'referee_difficulty_score': item.get('difficulty_score', 5.0),
            # 【新】在这里加入所有指标的计算
            'word_count': calculate_word_count(doc),  # 使用函数调用
            'readability_score': calculate_readability_en(prompt_text),
            'syntactic_complexity': get_syntactic_complexity(doc),
            'word_level_entropy': calculate_word_level_entropy(doc),
            'num_equations': num_eq,
            'num_variables': num_var,
            'non_linear_count': non_linear,
            'noise_ratio': noise,
            'second_highest_similarity_score': second_highest_scores[i]
        }
        all_problem_features.append(features)

    print("步骤2: 进行数据集级别分析 (使用Min-Max归一化)...")

    feature_keys = [
        'referee_difficulty_score',
        'word_count',
        'readability_score',
        'syntactic_complexity',
        'word_level_entropy',
        'num_equations',
        'num_variables',
        'non_linear_count',
        'noise_ratio',
        'second_highest_similarity_score'
    ]
    feature_matrix = np.array([[m[key] for key in feature_keys] for m in all_problem_features])

    # 1. 计算每个特征（每列）的最小值和最大值
    min_vals = np.min(feature_matrix, axis=0)
    max_vals = np.max(feature_matrix, axis=0)
    ranges = max_vals - min_vals

    # 2. 处理特殊情况：如果一个特征的所有值都相同 (range=0)，避免除以零
    # 我们将range为0的特征的range设置为1，这样(x-min)/range会等于0，不会产生错误
    ranges[ranges == 0] = 1.0

    # 3. 应用最小-最大归一化公式: (X - X_min) / (X_max - X_min)
    # 这会将每个特征的值都缩放到 [0, 1] 区间
    normalized_matrix = (feature_matrix - min_vals) / ranges

    # 4. 定义权重 (这里我们继续使用之前推荐的通用权重)
    difficulty_weights = np.array([
        -0.13,  # referee_difficulty_score
        0.09,  # word_count
        -0.10,  # readability_score
        0.05,  # syntactic_complexity
        0.15,  # word_level_entropy
        -0.15,  # num_equations
        -0.15,  # num_variables
        0.00,  # non_linear_count
        0.20,  # noise_ratio
        0.00  # second_highest_similarity_score
    ])

    # 5. 直接计算最终难度分数，并将其缩放到 0-10 的范围
    # (归一化后的特征与权重相乘，结果求和，再乘以10)
    # 注意：这里我们不再需要调用独立的 calculate_combined_difficulty 函数
    difficulty_scores = np.dot(normalized_matrix, difficulty_weights) * 10.0

    # --- 步骤3: 整合所有结果并输出 ---
    print("步骤3: 整合所有结果并输出...")
    for i, item in enumerate(data):
        # 【新】输出的JSON结构也更丰富了
        item['difficulty_analysis'] = {
            'referee': {
                'original_score': all_problem_features[i]['referee_difficulty_score']
            },
            'linguistic': {
                'word_count': all_problem_features[i]['word_count'],
                'readability_score': all_problem_features[i]['readability_score'],
                'syntactic_complexity': all_problem_features[i]['syntactic_complexity'],
                'word_level_entropy': all_problem_features[i]['word_level_entropy'],
            },
            'logical_mathematical': {
                'num_variables': all_problem_features[i]['num_variables'],
                'num_equations': all_problem_features[i]['num_equations'],
                'non_linear_count': all_problem_features[i]['non_linear_count'],
                'noise_ratio': all_problem_features[i]['noise_ratio']
            },
            'dataset_level': {
                'second_highest_similarity_score': all_problem_features[i]['second_highest_similarity_score']
            },
            'combined_difficulty_score': difficulty_scores[i]
        }
    print("步骤4: 对最终结果按ID进行自然排序...")

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

    # 对包含分析结果的 data 列表进行排序
    sorted_data = sorted(data, key=sort_key)
    # 输出文件现在也包含整体统计信息
    dataset_level_stats = {
        'difficulty_distribution': {
            'mean': np.mean(difficulty_scores),
            'std_dev': np.std(difficulty_scores),
            'min': np.min(difficulty_scores),
            'max': np.max(difficulty_scores),
            'median': np.median(difficulty_scores)
        }
    }
    output_data = {
        'dataset_level_stats': dataset_level_stats,
        'problems': sorted_data
    }

    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)




    percentile_25_score = 0.0
    if len(difficulty_scores) > 0:
        # 使用 NumPy 的 percentile 函数来精确计算第25个百分位数
        # 这会自动处理排序和索引，比手动计算更准确、更简单
        percentile_25_score = np.percentile(difficulty_scores, 25)

    print("\n--- 数据集整体难度分析 ---")
    dist = dataset_level_stats['difficulty_distribution']
    print(
        f"综合难度分数分布: 平均分={dist['mean']:.2f}, 标准差={dist['std_dev']:.2f}, 范围=[{dist['min']:.2f}, {dist['max']:.2f}]")

    # 打印结果
    print(f"得分在最低的25%分位点上的分数是: {percentile_25_score:.2f}")




    print("\n--- 数据集整体难度分析 ---")
    dist = dataset_level_stats['difficulty_distribution']
    print(
        f"综合难度分数分布: 平均分={dist['mean']:.2f}, 标准差={dist['std_dev']:.2f}, 范围=[{dist['min']:.2f}, {dist['max']:.2f}]")


# ========================================================================


if __name__ == "__main__":
    # 1. 创建一个命令行参数解析器
    parser = argparse.ArgumentParser(description="Calculate difficulty scores for a dataset.")

    # 2. 定义程序可以接收的参数，并设置默认值
    #    这样脚本在没有命令行参数时也能使用预设的路径运行
    base_dir = r"dataset\8_CrossedCondition"
    default_input = os.path.join(base_dir, "CrossedCondition.json")
    default_output = os.path.join(base_dir, "CrossedCondition_calculate.json")

    parser.add_argument("--input_path", type=str, default=default_input,
                        help="Path to the input JSON file with problems.")

    parser.add_argument("--output_path", type=str, default=default_output,
                        help="Path to save the output JSON file with difficulty analysis.")

    # 3. 解析用户从命令行输入的参数
    args = parser.parse_args()

    # 4. 调用主处理函数，并将解析到的参数传递进去
    print(f"输入文件: {args.input_path}")
    print(f"输出文件: {args.output_path}")
    process_prompts(args.input_path, args.output_path)

    # 打印完成信息时也使用解析后的路径，保持一致
    print(f"处理完成！结果已保存至：{args.output_path}")