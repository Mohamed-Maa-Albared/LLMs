import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.llms import Ollama

from src.web_app.search_tools.advanced_search import AdvancedSearchTool
from src.web_app.search_tools.news_organization_credibility import (
    NewsOrganizationAnalyzer,
)


class SearchAgent:
    def __init__(self, model="gemma2:27b"):
        self.llm = Ollama(model=model)
        self.search_tool = AdvancedSearchTool()
        self.analyzer = NewsOrganizationAnalyzer()
        self.prompt_template = """
        Please use the following format to structure your response:
        Context: {context}
        Sources Information: {sources_info}
        Question: {question}
        Response:
        Executive Summary
        [Provide a concise 2-3 sentence answer to the question, your answer should be comprehensive to the question]
        Information Recency and Reliability
        [Discuss the timeliness of the information used and evaluate the overall reliability of the sources]
        Detailed Analysis
        [Offer a comprehensive examination of the topic, using subheadings for clarity]
        [Subheading]
        [Content]
        [Subheading]
        [Content]
        ...
        Conflicting Viewpoints
        [IF applicable, present any contradictory information or perspectives found in the sources]
        Practical Applications
        [Discuss how this information can be applied in real-world scenarios or suggest next steps for the user]
        Limitations and Future Considerations
        [Acknowledge any limitations in the current understanding of the topic and suggest areas for further research or monitoring]
        Remember to maintain a neutral, objective tone throughout your response and prioritize accuracy over comprehensiveness when information is limited or uncertain.
        """
        self.solution_chain = (
            {
                "context": RunnablePassthrough(),
                "question": RunnablePassthrough(),
                "sources_info": RunnablePassthrough(),
            }
            | PromptTemplate(
                template=self.prompt_template,
                input_variables=["context", "question", "sources_info"],
            )
            | self.llm
        )

    def _answer_question(self, question, context, sources_info):
        response = self.solution_chain.invoke(
            {
                "context": context,
                "question": question,
                "sources_info": sources_info,
            }
        )
        return response

    def agent_answer_question(self, query):
        async def async_search_and_answer():
            orgs_info = []
            search_results = await self.search_tool.quick_search(query)
            context = "\n".join([result["full_text"] for result in search_results])
            links = "\n".join([result["links"] for result in search_results])
            orgs = self.analyzer.match_links_to_orgs(links)
            for org in orgs:
                org_info = self.analyzer._format_org_info(org)
                orgs_info.append(org_info)
            sources_info = "\n".join(orgs_info).strip()
            answer = self._answer_question(query, context, sources_info)
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

        orgs_info = []
        orgs = {}
        add_sources = False  # TODO: Enhance the source adding to make the model, not focus too much on that but take the most important info from it
        context = "\n".join([result["full_text"] for result in search_results])
        formatted_links = "\n".join(
            ["\n" + result["link"] for result in search_results]
        )
        if add_sources:
            orgs = self.analyzer.match_links_to_orgs(formatted_links)
        print("Matched organizations that we have information about:", orgs)  # debug
        for org in orgs:
            org_info = self.analyzer.get_organization_info(org)
            orgs_info.append(org_info)
        sources_info = "\n".join(orgs_info).strip()
        answer = self._answer_question(query, context, sources_info)
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
