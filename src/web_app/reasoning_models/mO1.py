from typing import List, Tuple

from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.llms import Ollama


class ReasoningModel:
    def __init__(
        self, solution_model="llama3.2:latest", critique_model="llama3.2:latest"
    ):
        self.solution_llm = Ollama(model=solution_model)
        self.critique_llm = Ollama(model=critique_model)

        self.solution_template = """
        You are an expert problem solver tasked with providing a concrete, implementable solution to the given problem.
        Focus on practicality, efficiency, and clarity in your solution, think step-by-step then implement the solution.

        Reasoning steps:
        - [List reasoning steps here]

        Problem: {problem}

        Concrete Final Solution:
        Add the final solution here.
        """

        self.critique_template = """
        As a critical thinker and problem-solving expert, analyze the following solution to the given problem.
        Identify its strengths, weaknesses, and provide specific suggestions for improvement.
        If the solution is optimal and requires no further improvements, explicitly state this.

        You will receive a step-by-step reasoning and a final solution, and you are tasked with critiquing it.

        Problem: {problem}

        Current Solution:
        {current_solution}

        Weaknesses:
        - [List weaknesses here]

        Suggestions for improvement:
        - [List suggestions here]

        Is this solution optimal? (Yes/No):
        [Your answer here]
        """

        self.solution_chain = (
            {"problem": RunnablePassthrough()}
            | PromptTemplate(
                template=self.solution_template, input_variables=["problem"]
            )
            | self.solution_llm
        )

        self.critique_chain = (
            {
                "problem": RunnablePassthrough(),
                "current_solution": RunnablePassthrough(),
            }
            | PromptTemplate(
                template=self.critique_template,
                input_variables=["problem", "current_solution"],
            )
            | self.critique_llm
        )

    def parse_critique(self, critique_text: str) -> dict:
        critique = {
            "weaknesses": [],
            "suggestions": [],
            "is_optimal": False,
        }

        current_section = None
        for line in critique_text.split("\n"):
            line = line.strip()

            if line.lower().startswith("weaknesses:") or line.lower().startswith(
                "**weaknesses:"
            ):
                current_section = "weaknesses"
            elif line.lower().startswith(
                "suggestions for improvement:"
            ) or line.lower().startswith("**suggestions for improvement:"):
                current_section = "suggestions"
            elif line.lower().startswith(
                "is this solution optimal?"
            ) or line.lower().startswith("**is this solution optimal?"):
                critique["is_optimal"] = "yes" in line.lower()
            elif line.startswith("-") and current_section:
                critique[current_section].append(line[1:].strip())
            elif line and current_section:
                critique[current_section].append(line)

        return critique

    def solve_problem(
        self, problem: str, max_iterations: int = 3
    ) -> Tuple[str, List[dict]]:
        current_solution = None
        critiques = []

        for _ in range(max_iterations):

            # Generate solution
            if current_solution is None:
                current_solution = self.solution_chain.invoke({"problem": problem})
            else:
                enhanced_problem = f"{problem}\n\nConsider the following suggestions for improvement:\n{'; '.join(critiques[-1]['suggestions'])}"
                current_solution = self.solution_chain.invoke(
                    {"problem": enhanced_problem}
                )

            # Generate critique
            critique_text = self.critique_chain.invoke(
                {"problem": problem, "current_solution": current_solution}
            )

            critique = self.parse_critique(critique_text)
            critiques.append(critique)

            # Check if the solution is optimal
            if critique["is_optimal"]:
                break

        return current_solution, critiques
