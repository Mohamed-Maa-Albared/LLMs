from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.llms import Ollama


class Agent:
    def __init__(self, model="llama3.1:latest"):
        self.llm = Ollama(model=model)

    def create_chain(self, template, input_variables):
        return (
            {var: RunnablePassthrough() for var in input_variables}
            | PromptTemplate(template=template, input_variables=input_variables)
            | self.llm
        )


class PlannerAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chain = self.create_chain(self.template, ["problem"])

    template = """
    You are an expert problem-solving strategist. Your task is to create a detailed, step-by-step plan to solve the given problem.
    Use chain-of-thought reasoning to break down the problem and develop a comprehensive solution strategy.

    Problem: {problem}

    Follow these steps:
    1. Analyze the problem thoroughly. Consider all aspects and potential challenges.
    2. Break down the problem into smaller, manageable sub-problems or tasks.
    3. For each sub-problem or task, provide a detailed approach to solve it.
    4. Consider potential obstacles and how to overcome them.
    5. Reflect on your plan. Are there any weaknesses or areas for improvement?
    6. Revise and refine your plan based on your reflection.

    Detailed Plan:
    [Your detailed plan here, following the steps above]

    Final Reflection:
    [Reflect on your plan, considering its strengths, potential weaknesses, and overall effectiveness]
    """


class CriticAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chain = self.create_chain(self.template, ["problem", "original_plan"])

    template = """
    You are an expert critical thinker and problem-solving strategist. Your task is to analyze the given plan for solving a problem, identify its strengths and weaknesses, and then create an improved plan.

    Problem: {problem}

    Original Plan:
    {original_plan}

    Follow these steps:
    1. Carefully analyze the original plan, considering its approach, thoroughness, and potential effectiveness.
    2. Identify and list the strengths of the original plan.
    3. Identify and list the weaknesses or areas for improvement in the original plan.
    4. Using chain-of-thought reasoning, develop an improved plan that addresses the weaknesses and builds upon the strengths of the original plan.
    5. Reflect on your improved plan. How does it compare to the original? What makes it better?
    6. If necessary, further refine your improved plan based on your reflection.

    Analysis of Original Plan:
    [Your analysis here, following steps 1-3]

    Improved Plan:
    [Your improved plan here, following steps 4-6]

    Final Reflection:
    [Reflect on how your improved plan addresses the problem more effectively than the original plan]
    """


class ImplementerAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chain = self.create_chain(self.template, ["problem", "improved_plan"])

    template = """
    You are an expert problem-solver and implementer. Your task is to take the improved plan for solving a problem and create a concrete, actionable implementation of that plan.

    Problem: {problem}

    Improved Plan:
    {improved_plan}

    Follow these steps:
    1. Carefully review the improved plan and the original problem.
    2. Break down the plan into specific, actionable steps.
    3. For each step, provide detailed instructions on how to execute it.
    4. Consider potential challenges in implementation and provide contingency plans.
    5. If the implementation involves code, provide code snippets or pseudocode where appropriate.
    6. Reflect on your implementation. Is it complete? Are there any areas that need further clarification or refinement?
    7. Based on your reflection, make any necessary adjustments to your implementation.

    Detailed Implementation:
    [Your detailed implementation here, following steps 1-5]

    Final Reflection and Adjustments:
    [Reflect on your implementation and make any final adjustments, following step 6]

    Final Implementation:
    [the final full optimal implementation goes here, following step 7]
    """


class MultiAgentReasoner:
    def __init__(self, model):
        self.planner = PlannerAgent(model=model)
        self.critic = CriticAgent(model=model)
        self.implementer = ImplementerAgent(model=model)

    def solve_problem(self, problem: str) -> str:
        # Step 1: Create initial plan
        initial_plan = self.planner.chain.invoke({"problem": problem})
        # Step 2: Critique and improve plan
        improved_plan = self.critic.chain.invoke(
            {"problem": problem, "original_plan": initial_plan}
        )
        # Step 3: Implement improved plan
        implementation = self.implementer.chain.invoke(
            {"problem": problem, "improved_plan": improved_plan}
        )

        return implementation
