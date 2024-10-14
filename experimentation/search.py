import asyncio
import re

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import (
    DuckDuckGoSearchAPIWrapper,
    GoogleSearchAPIWrapper,
)


class WebSearcher:
    def __init__(self, use_ddg=True, use_google=True):
        load_dotenv()
        self.use_ddg = use_ddg
        self.use_google = use_google
        if use_ddg:
            self.wrapper = DuckDuckGoSearchAPIWrapper(max_results=5)
            self.ddg_tool = DuckDuckGoSearchResults(api_wrapper=self.wrapper)
        if use_google:
            self.google_search = GoogleSearchAPIWrapper()

    async def search(self, query, max_results=5):
        results = []
        if self.use_ddg:
            results.extend(await self._search_ddg(query))
        if self.use_google:
            results.extend(await self._search_google(query))

        # Deduplicate results
        unique_results = []
        seen_urls = set()
        for result in results:
            if result["url"] not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result["url"])

        return unique_results[:max_results]

    async def _search_ddg(self, query):
        response = self.ddg_tool.invoke({"query": query})
        urls = self._extract_urls(response)
        return await self._process_urls(urls, "DuckDuckGo")

    async def _search_google(self, query):
        results = self.google_search.results(query, num_results=10)
        urls = [result.get("link", "") for result in results]
        return await self._process_urls(urls, "Google")

    def _extract_urls(self, response):
        url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
        return list(set(re.findall(url_pattern, response)))

    async def _process_urls(self, urls, source):
        results = []
        for url in urls:
            content = await self._fetch_url_content(url)
            if content:
                important_content = self._extract_important_content(content)
                results.append(
                    {"url": url, "content": important_content, "source": source}
                )
        return results

    async def _fetch_url_content(self, url):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as response:
                    return await response.text()
            except Exception as e:
                print(f"Error fetching {url}: {str(e)}")
                return None

    def _extract_important_content(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_="content")
        )

        if main_content:
            paragraphs = main_content.find_all("p")
            text = " ".join(p.get_text().strip() for p in paragraphs)
        else:
            text = " ".join(p.get_text().strip() for p in soup.find_all("p"))

        text = re.sub(r"\s+", " ", text).strip()
        return text[:1000]


# Example usage
async def main():
    # Create a WebSearcher object with both DuckDuckGo and Google
    searcher = WebSearcher(use_ddg=True, use_google=True)

    # Perform a search
    query = "What is happening today in Palestine?"
    results = await searcher.search(query, max_results=10)

    # Print results
    for result in results:
        print(f"URL: {result['url']}")
        print(f"Source: {result['source']}")
        print(f"Content: {result['content']}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
