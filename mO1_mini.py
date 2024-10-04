from typing import List, Tuple

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.llms import Ollama


class ReasoningModel:
    def __init__(self, model="llama3.1:latest"):
        self.llm = Ollama(model=model)

        self.template = """
        You are a world-class AI system, capable of complex reasoning and reflection. 
        Reason through the query inside <thinking> tags, and then provide your final response inside <output> tags. 
        If you detect that you made a mistake in your reasoning at any point, correct yourself inside <reflection> tags.

        Problem: {problem}

        <thinking>
        [Your reasoning about the problem goes here]
        </thinking>

        <Reflection>
        [Your Reflection about the reasoning steps goes here if needed]
        </Reflection>

        <output>
        [Your final solution to the problem goes here]
        </output>
        """

        self.solution_chain = (
            {"problem": RunnablePassthrough()}
            | PromptTemplate(template=self.template, input_variables=["problem"])
            | self.llm
        )

    def solve_problem(self, problem: str) -> Tuple[str, List[dict]]:
        solution = self.solution_chain.invoke(
            {"problem": problem + "\n Think carefully"}
        )
        return (
            solution,
            [],
        )  # Return an empty list for critiques as we're not using them

    def parse_response(self, response: str) -> dict:
        parsed = {"thinking": "", "output": "", "reflection": ""}

        thinking_start = response.find("<thinking>")
        thinking_end = response.find("</thinking>")
        if thinking_start != -1 and thinking_end != -1:
            parsed["thinking"] = response[thinking_start + 10 : thinking_end].strip()

        output_start = response.find("<output>")
        output_end = response.find("</output>")
        if output_start != -1 and output_end != -1:
            parsed["output"] = response[output_start + 8 : output_end].strip()

        reflection_start = response.find("<reflection>")
        reflection_end = response.find("</reflection>")
        if reflection_start != -1 and reflection_end != -1:
            parsed["reflection"] = response[
                reflection_start + 12 : reflection_end
            ].strip()

        return parsed


# Example usage
if __name__ == "__main__":
    model = ReasoningModel()
    problem = "Create snake in python"
    solution, _ = model.solve_problem(problem)
    parsed_solution = model.parse_response(solution)

    print("Thinking:", parsed_solution["thinking"])
    print("\nOutput:", parsed_solution["output"])
    if parsed_solution["reflection"]:
        print("\nReflection:", parsed_solution["reflection"])
