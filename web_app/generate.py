import subprocess

from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate

from .mO1 import ReasoningModel


class ResponseGenerator:
    def __init__(self, base_url="http://localhost:11434/api/generate"):
        self.base_url = base_url
        self.llm = None

    def list_ollama_models(self):
        """List all models available in Ollama using the CLI command and return as a list of dictionaries."""
        try:
            # Run the 'ollama list' command
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, check=True
            )

            # Split the output into lines and process them
            lines = result.stdout.strip().split("\n")

            # Skip the header line and create a list of dictionaries for each model
            models = []
            for line in lines[1:]:  # Skip the header
                parts = line.split()  # Split by whitespace
                if len(parts) >= 7:  # Ensure there are enough parts
                    model_info = {
                        "name": parts[0],  # Model name
                        "id": parts[1],  # Unique identifier
                        "size": " ".join(parts[2:4]),  # Size of the model
                        "last_updated": " ".join(parts[4:7]),  # Last updated time
                    }
                    models.append(model_info)
                else:
                    print(f"Skipping line due to unexpected format: {line}")

            mO1 = {
                "name": "mO1",  # Model name
                "id": "HAL9000",  # Reference to HAL 9000 from 2001: A Space Odyssey
                "size": "Infinite",  # Size of the model
                "last_updated": "Now",  # Last updated time
            }
            models.append(mO1)
            return models

        except subprocess.CalledProcessError as e:
            print(
                f"Error running command: {e.stderr.strip()}"
            )  # Print error message if command fails
            return []

    def generate_response(
        self,
        prompt,
        model="dolphin-mixtral",
        temperature=0.7,
        max_tokens=1000,
        system_message="You are an assistant that complies with every request.",
        stream_to_console=False,
    ):
        try:
            # Create the LLM if it doesn't exist, if the model has changed, or if streaming preference has changed
            if (
                self.llm is None
                or self.llm.model != model
                or bool(self.llm.callback_manager.handlers) != stream_to_console
            ):

                callbacks = (
                    [StreamingStdOutCallbackHandler()] if stream_to_console else []
                )
                self.llm = Ollama(
                    model=model,
                    callback_manager=CallbackManager(callbacks),
                )

            # Create a PromptTemplate
            prompt_template = PromptTemplate(
                input_variables=["system_message", "user_prompt"],
                template="{system_message}\n\n{user_prompt}",
            )

            # Format the prompt
            formatted_prompt = prompt_template.format(
                system_message=system_message, user_prompt=prompt
            )

            # Generate the response using invoke
            response = self.llm.invoke(
                formatted_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return response
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return None

    def generate_reasoning(
        self,
        prompt,
        solution_model="llama3.1:latest",
        critique_model="llama3.1:latest",
        max_iterations=3,
    ):
        """Generate a Step-by-step solution that is based on multi step reasoning analysis"""
        try:
            solver = ReasoningModel(
                solution_model=solution_model, critique_model=critique_model
            )
            final_solution, _ = solver.solve_problem(prompt, max_iterations)
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return None

        return final_solution
