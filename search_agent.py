import asyncio
import hashlib
import json
import os
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import aiohttp
import nltk
import requests
from bs4 import BeautifulSoup
from langchain.chains import LLMChain
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain_google_community import GoogleSearchAPIWrapper
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Set up environment variables for Google Search API
os.environ["GOOGLE_API_KEY"] = "AIzaSyAPH6b27p6eN_3u1pxFLuubg9UsANVFp48"
os.environ["GOOGLE_CSE_ID"] = "332c56fd5fdb44767"

# Download NLTK data
# nltk.download("punkt")
# nltk.download("stopwords")

# Initialize components
ddg_search = DuckDuckGoSearchRun()
google_search = GoogleSearchAPIWrapper()
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)

# Initialize Ollama model and embeddings
ollama_model = "llama3.1:latest"  # or any other model you have locally
llm = Ollama(model=ollama_model)
embeddings = OllamaEmbeddings(model=ollama_model)

# Credibility check constants
CREDIBLE_DOMAINS = {
    ".edu": 0.8,
    ".gov": 0.9,
    "nature.com": 0.9,
    "science.org": 0.9,
    "ieee.org": 0.8,
    "acm.org": 0.8,
    "nih.gov": 0.9,
    "who.int": 0.9,
}


async def fetch_url_content(
    session: aiohttp.ClientSession, url: str
) -> Tuple[str, str]:
    try:
        async with session.get(url, timeout=10) as response:
            content = await response.text()
            return url, content
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return url, ""


async def fetch_all_url_contents(urls: List[str]) -> Dict[str, str]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url_content(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        return dict(results)


def extract_text_from_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def calculate_text_similarity(text1: str, text2: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]


def check_credibility(url: str, content: str, query: str) -> float:
    domain = urlparse(url).netloc
    base_score = 0.5

    # Check domain credibility
    for credible_domain, score in CREDIBLE_DOMAINS.items():
        if credible_domain in domain:
            base_score = score
            break

    # Check content relevance
    relevance_score = calculate_text_similarity(query, content)

    # Check content length
    length_score = min(len(content) / 1000, 1)  # Normalize to 0-1

    # Calculate final credibility score
    credibility_score = (
        (base_score * 0.5) + (relevance_score * 0.3) + (length_score * 0.2)
    )
    return min(credibility_score, 1.0)  # Ensure score is between 0 and 1


async def get_search_results(query: str, num_results: int = 10) -> List[str]:
    try:
        ddg_results = ddg_search.run(query).split("\n")
    except Exception as e:
        print(f"Error with DuckDuckGo search: {e}")
        ddg_results = []

    try:
        google_results = google_search.run(query)
        if isinstance(google_results, str):
            google_results = [google_results]
        elif not isinstance(google_results, list):
            google_results = list(google_results)
    except Exception as e:
        print(f"Error with Google search: {e}")
        google_results = []

    all_results = list(set(ddg_results + google_results))[:num_results]
    return all_results


async def create_and_rank_documents(query: str, results: List[str]) -> List[Document]:
    url_contents = await fetch_all_url_contents(results)
    docs = []
    for url, html_content in url_contents.items():
        text_content = extract_text_from_html(html_content)
        chunks = text_splitter.split_text(text_content)
        credibility_score = check_credibility(url, text_content, query)
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
            "No documents were created. Check if url_contents is empty or if text extraction failed."
        )
        return []

    try:
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as e:
        print(f"Error creating FAISS index: {e}")
        print(f"Number of documents: {len(docs)}")
        # print(
        #    f"First document content: {docs[0].page_content if docs else 'No documents'}"
        # )
        return docs  # Return the documents without ranking if FAISS fails

    try:
        ranked_docs = vectorstore.similarity_search(query, k=len(docs))
    except Exception as e:
        print(f"Error performing similarity search: {e}")
        return docs  # Return the documents without ranking if similarity search fails

    # Combine similarity ranking with credibility score
    for doc in ranked_docs:
        doc.metadata["final_score"] = (
            doc.metadata.get("score", 0.5) + doc.metadata.get("credibility", 0.5)
        ) / 2

    return sorted(ranked_docs, key=lambda x: x.metadata["final_score"], reverse=True)


async def generate_response(
    query: str, use_cache: bool = True
) -> Tuple[str, List[str]]:
    cache_key = hashlib.md5(query.encode()).hexdigest()
    cache_file = f"cache_{cache_key}.json"

    if use_cache and os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cached_data = json.load(f)
        return cached_data["response"], cached_data["sources"]

    results = await get_search_results(query)
    ranked_docs = await create_and_rank_documents(query, results)

    context = "\n".join(
        [doc.page_content for doc in ranked_docs[:3]]
    )  # Use top 3 for context
    sources = [doc.metadata.get("source", "Unknown") for doc in ranked_docs[:3]]

    prompt_template = """
    You are an AI assistant tasked with providing accurate and nuanced answers based on the latest information available.
    Use the following context to answer the question. If the context doesn't contain enough information, use your general knowledge, but prioritize the given context:

    Context: {context}

    Question: {question}

    Provide a detailed and nuanced answer, and mention if there are any conflicting viewpoints in the sources:
    """

    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run(context=context, question=query)

    if use_cache:
        with open(cache_file, "w") as f:
            json.dump({"response": response, "sources": sources}, f)

    return response, sources


async def main():
    query = "What are the latest advancements in quantum computing?"
    response, sources = await generate_response(query)
    print("Response:", response)
    print("\nSources:")
    for source in sources:
        print(source)


if __name__ == "__main__":
    asyncio.run(main())
