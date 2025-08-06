# postprocessor.py
import re


def structure_response_into_data(data_list, input_path, separator="#", field="prompt", task_name=None):
    """
    根据任务类型，将模型的response构建到数据项中。
    对于特定任务，创建新的字段来存储response。
    对于其他任务，保留原有的追加或替换逻辑。
    """

    # 1. 定义从“任务名”到“新字段名”的映射
    #    您可以随时在这里添加新的任务和字段
    task_to_new_field_map = {
        "UselessCondition": "useless_conditions",
        "ConfusedCondition": "confused_conditions"
        # 以后还可以添加，例如：
        # "MisleadingCondition": "misleading_conditions"
    }

    for data_item in data_list:
        response = data_item.get("response", "").strip()
        prompt = data_item.get(field, "")

        if not response:
            continue

        # 2. 检查当前任务是否需要创建新字段
        if task_name in task_to_new_field_map:
            # **核心修改：不再修改 prompt，而是创建新字段**
            new_field_name = task_to_new_field_map[task_name]
            data_item[new_field_name] = response
            # （可选）可以考虑从 data_item 中删除 "response" 字段，让结构更干净
            # del data_item["response"]

        # 3. 对于其他任务，保留现有的逻辑
        elif task_name in ["Translate", "FormulaClarifier"]:
            data_item[field] = response
        elif task_name == "ContextGen":
            updated_prompt = f"{response}{separator}{prompt}"
            data_item[field] = updated_prompt
        elif task_name in ["MisleadingCondition", "AddCondition"] and input_path and "Second_Evolution" in input_path:
            # ... 保留您为 Second_Evolution 编写的特殊逻辑 ...
            sentences = [s for s in re.split(r'(?<=[.?!。？！])\s*', prompt) if s.strip()]
            if len(sentences) >= 2:
                main_part = "".join(sentences[:-1])
                last_sentence = sentences[-1]
                updated_prompt = f"{main_part.strip()}{separator}{response}{separator}{last_sentence.strip()}"
                data_item[field] = updated_prompt
            else:
                updated_prompt = f"{prompt}{separator}{response}"
                data_item[field] = updated_prompt
        else:
            # 默认的回退逻辑：追加到 prompt 后面
            updated_prompt = f"{prompt}{separator}{response}"
            data_item[field] = updated_prompt

    return data_list