import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_community.vectorstores import FAISS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from search import WebSearcher  # Import the WebSearcher class from search.py

# Set up environment variables
load_dotenv()


class SearchAgent:
    def __init__(
        self,
        use_ddg: bool = True,
        use_google: bool = False,
        model: str = "llama3.1:latest",
        chunk_size: int = 1000,
        chunk_overlap: int = 0,
        cache_duration: int = 1,  # in hours
    ):
        self.web_searcher = WebSearcher(use_ddg=use_ddg, use_google=use_google)
        self.llm = Ollama(model=model)
        self.embeddings = OllamaEmbeddings(model=model)
        self.text_splitter = CharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self.cache_duration = timedelta(hours=cache_duration)

        self.functions = [
            {
                "name": "search_web",
                "description": "Search the web for up-to-date information on a given query. Use this function when the query requires current information and facts about recent events.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"}
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "answer_without_search",
                "description": "Answer a query without searching the web, using only the AI's knowledge. This applies to interactive queries like hello how are you, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to answer",
                        }
                    },
                    "required": ["query"],
                },
            },
        ]

    @staticmethod
    def calculate_text_similarity(text1: str, text2: str) -> float:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    @staticmethod
    def extract_date(content: str) -> datetime:
        date_patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
            r"\b\d{2}/\d{2}/\d{4}\b",  # MM/DD/YYYY
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b",  # Month DD, YYYY
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    date = datetime.strptime(match, "%Y-%m-%d")
                except ValueError:
                    try:
                        date = datetime.strptime(match, "%m/%d/%Y")
                    except ValueError:
                        try:
                            date = datetime.strptime(match, "%b %d, %Y")
                        except ValueError:
                            continue
                dates.append(date)

        return max(dates) if dates else datetime.min

    @staticmethod
    def check_recency(content: str) -> float:
        extracted_date = SearchAgent.extract_date(content)
        if extracted_date == datetime.min:
            return 0.5  # Default score if no date found

        days_old = (datetime.now() - extracted_date).days
        if days_old <= 7:
            return 1.0
        elif days_old <= 30:
            return 0.9
        elif days_old <= 90:
            return 0.8
        elif days_old <= 180:
            return 0.7
        elif days_old <= 365:
            return 0.6
        else:
            return 0.5

    @staticmethod
    def check_credibility_and_recency(url: str, content: str, query: str) -> float:
        relevance_score = SearchAgent.calculate_text_similarity(query, content)
        length_score = min(len(content) / 1000, 1)
        recency_score = SearchAgent.check_recency(content)

        domain = urlparse(url).netloc
        authority_score = (
            0.8
            if any(domain.endswith(tld) for tld in [".gov", ".edu", ".org"])
            else 0.6
        )

        citation_score = 0.1 if re.search(r"\[\d+\]|\(.*?\d{4}.*?\)", content) else 0

        credibility_score = (
            (relevance_score * 0.3)
            + (length_score * 0.1)
            + (recency_score * 0.3)
            + (authority_score * 0.2)
            + (citation_score * 0.1)
        )
        return min(credibility_score, 1.0)

    async def create_and_rank_documents(
        self, query: str, search_results: List[Dict]
    ) -> List[Document]:
        docs = []
        for result in search_results:
            url = result["url"]
            content = result["content"]
            chunks = self.text_splitter.split_text(content)
            credibility_score = self.check_credibility_and_recency(url, content, query)
            docs.extend(
                [
                    Document(
                        page_content=chunk,
                        metadata={"source": url, "credibility": credibility_score},
                    )
                    for chunk in chunks
                ]
            )

        if not docs:
            print(
                "No documents were created. Check if search results are empty or if text extraction failed."
            )
            return []

        try:
            vectorstore = FAISS.from_documents(docs, self.embeddings)
            ranked_docs = vectorstore.similarity_search(query, k=len(docs))
        except Exception as e:
            print(f"Error creating FAISS index or performing similarity search: {e}")
            return docs  # Return the documents without ranking if FAISS fails

        for doc in ranked_docs:
            doc.metadata["final_score"] = (
                doc.metadata.get("score", 0.5) * 0.7
                + doc.metadata.get("credibility", 0.5) * 0.3
            )

        return sorted(
            ranked_docs, key=lambda x: x.metadata["final_score"], reverse=True
        )

    async def search_web(self, query: str) -> Tuple[str, List[str], str]:
        current_year = datetime.now().year
        enhanced_query = f"{query} {current_year}"
        results = await self.web_searcher.search(enhanced_query, max_results=10)

        if not results:
            print("No results from web search")
            return (
                "I'm sorry, but I couldn't find any relevant information for your query. The search didn't return any results. This could be due to network issues or limitations in the search service. Could you please try rephrasing your question or asking about a different topic?",
                [],
                "",
            )

        ranked_docs = await self.create_and_rank_documents(query, results)
        context = "\n".join(
            [doc.page_content for doc in ranked_docs[:3]]
        )  # Use top 3 for context
        sources = [doc.metadata.get("source", "Unknown") for doc in ranked_docs[:3]]

        prompt_template = """
        You are an AI assistant designed to provide accurate, up-to-date, and real-time answers based on the latest information available online. You have access to the Internet and can leverage the provided context to formulate your responses.

        Please use the following context to answer the question. If the context lacks sufficient information or appears outdated, kindly indicate this and supplement your response with the most recent information you can find:

        Context: {context}

        Question: {question}

        Current Date: {current_date}

        Brief Answer:
            <Start with a concise answer to the question.>
        Recency of Information:
            <Indicate how recent the information is and mention if there may be more current data available.>
        Detailed Analysis and Conflicting Viewpoints:
            <Provide a more in-depth discussion of key points, using bullet points or subheadings for clarity.>
            <Highlight any conflicting viewpoints present in the sources you reference.>
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question", "current_date"],
        )
        chain = LLMChain(llm=self.llm, prompt=prompt)
        response = chain.run(
            context=context,
            question=query,
            current_date=datetime.now().strftime("%Y-%m-%d"),
        )

        return response, sources, context

    def answer_without_search(self, query: str) -> Tuple[str, List[str]]:
        prompt = f"""
        You are a helpful AI assistant. Please respond to the following query:
        {query}
        
        If you don't have enough information to answer the query accurately, please state that clearly.
        """
        response = self.llm(prompt)
        return response, []

    async def generate_response(
        self, query: str, use_cache: bool = True
    ) -> Tuple[str, List[str], str]:
        cache_key = hashlib.md5(query.encode()).hexdigest()
        cache_file = f"cache_{cache_key}.json"
        context = ""

        if use_cache and os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            cache_age = datetime.now() - datetime.fromisoformat(
                cached_data["timestamp"]
            )
            if cache_age < self.cache_duration:
                return (
                    cached_data["response"],
                    cached_data["sources"],
                    cached_data.get("context", ""),
                )

        function_call_prompt = f"""
        Given the following query, determine which function should be called to best answer it:
        Query: {query}

        Available functions:
        {json.dumps(self.functions, indent=2)}

        Respond with ONLY the name of the function that should be called, either "search_web" or "answer_without_search", with no further explanation.
        """
        function_to_call = self.llm(function_call_prompt).strip()
        print(f"Function to call: {function_to_call}")

        if function_to_call == "search_web":
            response, sources, context = await self.search_web(query)
        else:
            response, sources = self.answer_without_search(query)

        if use_cache:
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "response": response,
                        "sources": sources,
                        "context": context,
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                )

        return response, sources, context


async def main():
    # Example usage
    agent = SearchAgent(use_ddg=True, use_google=True, model="llama3.1:latest")
    query = "Who are the US presidential candidates as of today?"
    response, sources, context = await agent.generate_response(query)
    print("Response:", response)
    print("\nSources:")
    for source in sources:
        print(source)


if __name__ == "__main__":
    asyncio.run(main())
