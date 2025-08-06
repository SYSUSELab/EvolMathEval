from abc import abstractmethod


class BaseLLM():

    @abstractmethod
    def generation_in_parallel(self, prompts):
        pass

    @abstractmethod
    def support_model_list(self):
        pass


def generation_result(LLM: BaseLLM, prompts, temperature=1):
    return LLM.generation_in_parallel(prompts)

def show_model_list(LLM: BaseLLM):
    return LLM.support_model_list()
