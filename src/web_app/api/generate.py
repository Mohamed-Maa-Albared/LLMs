from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate

from src.utils.config_load import ConfigLoader
from web_app.api.ollama_models import OllamaModelManager
from web_app.reasoning_models.mO1 import ReasoningModel as ReasoningModel_mO1
from web_app.reasoning_models.mO1_mini import ReasoningModel as ReasoningModel_mO1_mini
from web_app.reasoning_models.mO1V2 import MultiAgentReasoner as ReasoningModel_mO1V2


class ResponseGenerator:
    def __init__(self):
        self.config_loader = ConfigLoader()
        self.custom_models = self.config_loader.get_section("custom_models")
        self.api_settings = self.config_loader.get_section("api_settings")
        self.user_preferences = self.config_loader.get_section("user_preferences")

        self.base_url = self.api_settings.get(
            "base_url", "http://localhost:11434/api/generate"
        )
        self.llm = None
        self.model_manager = OllamaModelManager()

    def list_ollama_models(self, force_refresh=False):
        """List all models available in Ollama using the OllamaModelManager."""
        models = self.model_manager.list_ollama_models(force_refresh)

        # Add all custom models if they're not already in the list
        for custom_model in self.custom_models:
            if not any(model["name"] == custom_model["name"] for model in models):
                self.model_manager.add_custom_model(custom_model)
                models.append(custom_model)

        models = self.model_manager.filter_models(
            models, name=["nomic-embed-text:latest", "codellama:code"]
        )
        models = self.model_manager.sort_models(models)
        models = [{**d, **{"name": d["name"].replace(":latest", "")}} for d in models]
        return models

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
                or (
                    self.llm.callback_manager is not None
                    and bool(self.llm.callback_manager.handlers) != stream_to_console
                )
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

    def generate_reasoning_mO1(
        self,
        prompt,
        solution_model="llama3.1:latest",
        critique_model="llama3.1:latest",
        max_iterations=3,
    ):
        """Generate a Step-by-step solution that is based on multi step reasoning analysis"""
        try:
            solver = ReasoningModel_mO1(
                solution_model=solution_model, critique_model=critique_model
            )
            response, _ = solver.solve_problem(prompt, max_iterations)
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return None

        return response

    def generate_reasoning_mO1_mini(
        self,
        prompt,
        model="llama3.1:latest",
    ):
        """Generate a Step-by-step solution that is based on multi step reasoning analysis"""
        try:
            solver = ReasoningModel_mO1_mini(model=model)
            response = solver.solve_problem(prompt)
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return None

        return response

    def generate_reasoning_mO1V2(
        self,
        prompt,
        model="llama3.1:latest",
    ):
        """Generate a Step-by-step solution that is based on multi step reasoning analysis"""
        try:
            solver = ReasoningModel_mO1V2(model=model)
            response = solver.solve_problem(prompt)
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return None

        return response
