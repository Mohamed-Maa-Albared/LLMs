import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.llms import Ollama

from src.web_app.search_tools.advanced_search import AdvancedSearchTool


class SearchAgent:
    def __init__(self, model="gemma2:27b"):
        self.llm = Ollama(model=model)
        self.search_tool = AdvancedSearchTool()
        self.prompt_template = """
        You are an AI assistant designed to provide accurate, up-to-date, and real-time answers based on the latest information available online. You have access to the Internet and can leverage the provided context to formulate your responses.

        Please use the following context to answer the question. If the context lacks sufficient information or appears outdated, kindly indicate this and supplement your response with the most recent information you can find:

        Context: {context}

        Question: {question}

        Brief Answer:
            <Start with a concise yet comprehensive answer to the question.>
        Recency of Information:
            <Indicate how recent the information is and mention if there may be more current data available.>
        Detailed Analysis:
            <Provide a more in-depth discussion of key points, using bullet points or subheadings for clarity. >
        Conflicting Viewpoints:
            <Highlight any conflicting viewpoints present in the sources you reference, use verbatim quotes and mention the source of the quote.>
        """
        self.solution_chain = (
            {
                "context": RunnablePassthrough(),
                "question": RunnablePassthrough(),
            }
            | PromptTemplate(
                template=self.prompt_template, input_variables=["context", "question"]
            )
            | self.llm
        )

    def _answer_question(self, question, context):
        response = self.solution_chain.invoke(
            {
                "context": context,
                "question": question,
            }
        )
        return response

    def agent_answer_question(self, query):
        async def async_search_and_answer():
            search_results = await self.search_tool.quick_search(query)
            context = "\n".join([result["full_text"] for result in search_results])
            answer = self._answer_question(query, context)
            return answer

        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, we can't use run_until_complete
            return asyncio.ensure_future(async_search_and_answer())
        else:
            return loop.run_until_complete(async_search_and_answer())

    def synchronous_answer_question(self, query):
        def run_async_search():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.search_tool.quick_search(query))

        with ThreadPoolExecutor() as executor:
            search_results = executor.submit(run_async_search).result()

        context = "\n".join([result["full_text"] for result in search_results])
        answer = self._answer_question(query, context)

        formatted_links = "\n".join(
            ["\n" + result["link"] for result in search_results]
        )
        answer = f"{answer}\n\n **Sources:** \n{formatted_links}"
        return answer


# Example usage
def main():
    qa_system = SearchAgent()
    question = "What is happening today in Palestine?"
    answer = qa_system.synchronous_answer_question(question)
    print("Answer:", answer)


if __name__ == "__main__":
    main()
