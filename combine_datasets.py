import json
import os
from datetime import datetime
import argparse  # 导入 argparse 库

def combine_and_renumber_datasets(file_path_1, file_path_2, output_dir):
    """
    加载、合并、重新编号并保存两个数据集。
    现在所有路径都通过参数传入。
    """
    # 定义输出文件的基础名称 (可以保持固定)
    output_filename_base = 'CombinedProblems'

    # --- 数据加载 ---
    try:
        print(f"正在加载文件 1: {file_path_1}")
        with open(file_path_1, 'r', encoding='utf-8') as f:
            problems_from_file1 = json.load(f)

        print(f"正在加载文件 2: {file_path_2}")
        with open(file_path_2, 'r', encoding='utf-8') as f:
            data_from_file2 = json.load(f)
            # 只提取 "problems" 键对应的值
            problems_from_file2 = data_from_file2.get('problems', [])
            if not problems_from_file2:
                print(f"警告: 在文件 {file_path_2} 中未找到 'problems' 键或其内容为空。")

    except FileNotFoundError as e:
        print(f"错误: 文件未找到。请检查路径是否正确。 {e}")
        return
    except json.JSONDecodeError as e:
        print(f"错误: JSON文件格式不正确。 {e}")
        return
    except Exception as e:
        print(f"发生未知错误: {e}")
        return

    # --- 数据处理 ---
    print("正在拼接两个数据集...")
    combined_problems = problems_from_file1 + problems_from_file2
    print(f"拼接完成，共计 {len(combined_problems)} 个问题。")

    def sort_key(item):
        item_id = item.get('id', '0_0')
        try:
            part1, part2 = map(int, str(item_id).split('_'))
            return (part1, part2)
        except (ValueError, TypeError):
            # 兼容单个数字的ID（例如在重新编号后又用于此脚本的情况）
            try:
                return (int(item_id), 0)
            except (ValueError, TypeError):
                 return (float('inf'), float('inf')) # 无法解析的ID排在最后

    # 对合并后的列表进行排序
    sorted_combined_problems = sorted(combined_problems, key=sort_key)
    print("排序完成。")

    # --- 文件保存 ---
    try:
        print(f"正在创建输出目录: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

        # 定义两个输出文件的完整路径
        stable_output_path = os.path.join(output_dir, f"{output_filename_base}.json")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        timestamped_output_path = os.path.join(output_dir, f"{output_filename_base}_{timestamp}.json")

        # 保存到第一个文件 (标准名称)
        print(f"正在保存到: {stable_output_path}")
        with open(stable_output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_combined_problems, f, ensure_ascii=False, indent=4)

        # 保存到第二个文件 (带时间戳)
        print(f"正在保存到: {timestamped_output_path}")
        with open(timestamped_output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_combined_problems, f, ensure_ascii=False, indent=4)

        print("\n处理成功！所有文件已保存。")

    except Exception as e:
        print(f"在保存文件时发生错误: {e}")


# 运行主函数
if __name__ == "__main__":
    # 1. 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="合并、重新编号并保存两个JSON数据集。")

    # 2. 定义需要接收的命令行参数
    parser.add_argument(
        '--input1',
        type=str,
        default='dataset/8_CrossedCondition/Second_Evolution/CrossedCondition.json',
        help='第一个输入JSON文件的路径 (格式为列表)。'
    )
    parser.add_argument(
        '--input2',
        type=str,
        default='dataset/8_CrossedCondition/CrossedCondition_cleaned.json',
        help='第二个输入JSON文件的路径 (格式为包含problems键的对象)。'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default='dataset/9_CombinedProblems',
        help='保存合并后文件的输出目录。'
    )

    # 3. 解析命令行传入的参数
    args = parser.parse_args()

    # 4. 将解析到的参数传递给主函数来执行
    combine_and_renumber_datasets(
        file_path_1=args.input1,
        file_path_2=args.input2,
        output_dir=args.output_dir
    )