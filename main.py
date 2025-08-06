import subprocess
# 使用原始字符串（raw string）来避免路径问题
python_path = r"..\venv\Scripts\python.exe"

# 2. 為 fitness.py 指定的特殊虛擬環境 Python 解釋器路徑
fitness_python_path = r"e:\trusted-eval\venv\Scripts\python.exe"
# # 使用原始字符串（raw string）来避免路径问题
# python_path = r"path/to/your/python.exe"
#
# # 2. 為 fitness.py 指定的特殊虛擬環境 Python 解釋器路徑
# fitness_python_path = r"path/to/your/python.exe"

commandsf = [
    f"{python_path} formula_generation.py",
    f"{python_path} Approximate_substitution.py --input dataset/0_InitialData/step1/InitialData.json --output dataset/0_InitialData/InitialData_Complete_cleaned.json",
    f"{python_path} trusted_gpt.py --step UselessCondition --input_path ./dataset/0_InitialData/InitialData_Complete_cleaned.json --output_path ./dataset/1_UselessCondition/Complete",
    f"{python_path} trusted_gpt.py --step ConfusedCondition --input_path ./dataset/1_UselessCondition/Complete/UselessCondition.json --output_path ./dataset/2_ConfusedCondition/Complete",
    f"{python_path} questionGeneration.py --input_path ./dataset/2_ConfusedCondition/Complete/ConfusedCondition.json --output_path ./dataset/3_Translated/Translated_Complete.json",
    f"{python_path} trusted_gpt.py --step FormulaClarifier --input_path ./dataset/3_Translated/Translated_Complete.json --output_path ./dataset/4_FormulaClarifier/Complete",
    f"{python_path} trusted_gpt.py --step MisleadingCondition --input_path ./dataset/4_FormulaClarifier/Complete/FormulaClarifier.json --output_path ./dataset/5_MisleadingCondition/Complete",
    f"{python_path} trusted_gpt.py --step ContextGen --input_path ./dataset/5_MisleadingCondition/Complete/MisleadingCondition.json --output_path ./dataset/6_ContextGen/Complete",
    f"{python_path} trusted_gpt.py --step AddCondition --input_path ./dataset/6_ContextGen/Complete/ContextGen.json --output_path ./dataset/7_AddCondition/Complete",
    f"{python_path} cross.py --input_path ./dataset/7_AddCondition/Complete/AddCondition.json --output_path ./dataset/8_CrossedCondition/Complete/CrossedCondition.json",
    f"{python_path} Evolutionary_scoring.py --file_path ./dataset/8_CrossedCondition/Complete/CrossedCondition.json",
    f"{fitness_python_path} fitness.py --input_path ./dataset/8_CrossedCondition/Complete/CrossedCondition.json --output_path ./dataset/8_CrossedCondition/Complete/CrossedCondition_calculate.json",
    f"{python_path} extract_low_difficulty.py --input_path ./dataset/8_CrossedCondition/Complete/CrossedCondition_calculate.json --low_score_output_path ./dataset/8_CrossedCondition/Second_Evolution/Complete/CrossedCondition_low_difficulty.json --high_score_output_path ./dataset/8_CrossedCondition/Complete/CrossedCondition_cleaned.json",
    f"{python_path} trusted_gpt.py --step MisleadingCondition --input_path ./dataset/8_CrossedCondition/Second_Evolution/Complete/CrossedCondition_low_difficulty.json --output_path ./dataset/5_MisleadingCondition/Second_Evolution/Complete",
    f"{python_path} trusted_gpt.py --step ContextGen --input_path ./dataset/5_MisleadingCondition/Second_Evolution/Complete/MisleadingCondition.json --output_path ./dataset/6_ContextGen/Second_Evolution/Complete",
    f"{python_path} trusted_gpt.py --step AddCondition --input_path ./dataset/6_ContextGen/Second_Evolution/Complete/ContextGen.json --output_path ./dataset/7_AddCondition/Second_Evolution/Complete",
    f"{python_path} cross.py --input_path ./dataset/7_AddCondition/Second_Evolution/Complete/AddCondition.json --output_path ./dataset/8_CrossedCondition/Second_Evolution/Complete/CrossedCondition.json",
    f"{python_path} combine_datasets.py --input1 dataset/8_CrossedCondition/Second_Evolution/Complete/CrossedCondition.json --input2 dataset/8_CrossedCondition/Complete/CrossedCondition_cleaned.json --output_dir dataset/9_CombinedProblems/Complete",
    # f"{python_path} trusted_gpt.py --eval --input_path ./dataset/9_CombinedProblems/Complete/CombinedProblems.json --output_path ./evaluation_results/Complete",
    # f"{python_path} ExtractAnswer.py --target_filename evaluation_results.json --output_dir ./results_analysis/Complete --results_dir ./evaluation_results/Complete",
]

all_command_groups = [commandsf]
for i, group in enumerate(all_command_groups):
    for command in group:
        print(f"正在执行命令: {command}")
        try:
            subprocess.run(command, shell=True, check=True)
            print(f"成功完成: {command}\n")
        except subprocess.CalledProcessError as e:
            print(f"执行命令时发生错误: {command}")
            print(f"报错: {e.returncode}")
            print(f"输出: {e.stdout}")
            print(f"错误输出: {e.stderr}")
            break
        except FileNotFoundError:
            print(f"错误: 找不到命令或文件。 {command.split()[0]}")
            break

print("所有命令执行完成。")
