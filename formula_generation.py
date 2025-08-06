import random
import json
import numpy as np
import os

# 常量
VALUE_RANGE = (5.0, 15.0)  # 小数范围
COEF_CHOICES = [i for i in range(-5, 6) if i != 0] + [-0.5, 0.5]  # 只允许整数或0.5/-0.5
NUM_TERMS_RANGE = (1, 3)  # 每个方程左边1到3个变量
OPERATIONS = ['*', '/']  # 允许乘法或除法
AVAILABLE_VARS = ['x', 'y', 'z', 'm', 'n']  # 新变量名列表


# 步骤 (ii) 生成方程组
def save_to_json(num_problems, num_vars, filename='./dataset/0_InitialData/step1/InitialData.json'):
    # 创建文件夹路径（如果不存在）
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    all_data = []
    # 使用固定种子便于调试和复现，若要每次不同，可改回 random.random()
    # random.seed(42)
    # np.random.seed(42)

    for i in range(1, num_problems + 1):
        # 增加一个循环，直到成功生成一个有效的方程组
        while True:
            formulas, answer = generate_sparse_linear_problem(num_vars)
            # 如果生成成功（返回的不是None），则跳出循环
            if formulas is not None:
                break
            # 可选：如果想观察重试次数，可以取消下面的注释
            # else:
            #     print(f"问题 {i} 生成失败，正在重试...")

        prompt = ' # '.join(formulas)
        answer = ' # '.join(answer)
        all_data.append({
            'id': i,
            'prompt': prompt,
            'answer': answer
        })

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)


def generate_sparse_linear_problem(num_vars=5, num_equations=5, coef_choices=COEF_CHOICES, operations=OPERATIONS):
    # 确保n是最后一个变量
    var_names = AVAILABLE_VARS[:num_vars - 1] + ['n']

    # 步骤 1: 随机生成整数解
    solution = np.array([random.randint(1, 20) for _ in range(num_vars)])

    # 步骤 2: 构造稀疏方程组
    A = np.zeros((num_equations, num_vars), dtype=float)

    # 生成前num_equations-1个方程（不含n）
    for i in range(num_equations - 1):
        num_terms = random.randint(NUM_TERMS_RANGE[0], min(NUM_TERMS_RANGE[1], num_vars - 1))
        chosen_indices = random.sample(range(num_vars - 1), num_terms)
        for j in chosen_indices:
            coef = random.choice(coef_choices)
            A[i, j] = coef

    # 生成最后一个方程（必须包含n和至少一个其他变量）
    # 确保n的系数不为0
    num_other_terms_in_last_eq = random.randint(1, min(NUM_TERMS_RANGE[1] - 1, num_vars - 1))
    other_indices = random.sample(range(num_vars - 1), num_other_terms_in_last_eq)
    chosen_indices_last_eq = other_indices + [num_vars - 1]  # 添加n
    for j in chosen_indices_last_eq:
        coef = random.choice(coef_choices)
        A[num_equations - 1, j] = coef

    # 如果n的系数意外为0，则重新生成（虽然概率很低）
    if A[num_equations - 1, num_vars - 1] == 0:
        return None, None  # 返回None表示生成失败，让上层循环重试

    # 步骤 3: 验证前num_equations-1个方程对于变量x,y,z,m是否满秩
    # 这是为了确保整个系统有唯一解
    A_without_n = A[:num_equations - 1, :num_vars - 1]
    if np.linalg.matrix_rank(A_without_n) < num_vars - 1:
        # print("Debug: 系统秩不足，重新生成...")
        return None, None  # 返回None表示生成失败

    # ==============================================================================
    # 新增逻辑：步骤 4: 验证第一个方程对于求解n是否“必要”
    # ==============================================================================

    # 找到最后一个方程中，除了n之外，还涉及了哪些变量。获取它们的列索引。
    last_eq_vars_indices = np.where(A[num_equations - 1, :num_vars - 1] != 0)[0]

    # 如果最后一个方程只有n（例如 2n = 10），那么第一个方程自然不是必需的。
    # 我们的生成逻辑已经保证了这种情况不会发生，但做一个检查更稳健。
    if len(last_eq_vars_indices) > 0:
        # 构建一个“子矩阵”，它由“除了第一个和最后一个方程之外的所有方程”（行）
        # 和“最后一个方程中涉及的变量”（列）组成。
        # 行索引：1 到 num_equations - 2
        # 列索引：last_eq_vars_indices
        A_sub_check = A[1:num_equations - 1, last_eq_vars_indices]

        # 如果这个子矩阵的秩 等于 它所包含的变量数，
        # 这意味着仅用方程2, 3, 4, ... 就可以完全确定这些变量的值。
        # 那么方程1对于求解n就是多余的。
        if np.linalg.matrix_rank(A_sub_check) == len(last_eq_vars_indices):
            # print(f"Debug: 第一个方程对于求解n不是必需的（子系统秩 {np.linalg.matrix_rank(A_sub_check)} == 变量数 {len(last_eq_vars_indices)}），重新生成...")
            return None, None  # 返回None表示生成失败，需要重试

    # 步骤 5: 计算右侧常数项 b
    b = A @ solution

    # 转为公式字符串：省略乘号
    formulas = []
    for i in range(num_equations):
        terms = []
        for j in range(num_vars):
            coef = A[i, j]
            if coef != 0:
                # 对系数和变量进行格式化
                if coef == 1:
                    terms.append(f'{var_names[j]}')
                elif coef == -1:
                    terms.append(f'-{var_names[j]}')
                # 处理整数系数，避免不必要的 .0
                elif coef == int(coef):
                    terms.append(f'{int(coef)}{var_names[j]}')
                else:
                    terms.append(f'{coef}{var_names[j]}')

        # 用 " + " 连接各项，然后替换掉 "+ -" 这种不美观的写法
        left = ' + '.join(terms).replace('+ -', '- ')

        # 处理右侧常数项，避免不必要的 .0
        b_val = b[i]
        if b_val == int(b_val):
            b_val = int(b_val)

        formulas.append(f'{left} = {b_val}')

    answer = [f'{v} = {val}' for v, val in zip(var_names, solution)]
    return formulas, answer


# 示例用法
if __name__ == '__main__':
    save_to_json(num_problems=10, num_vars=5)