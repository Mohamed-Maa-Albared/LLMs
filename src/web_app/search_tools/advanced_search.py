import asyncio
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class AdvancedSearchTool:
    def __init__(self, max_results=8):
        self.max_results = max_results
        self.base_url = "https://duckduckgo.com/html/"
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

    async def _search_and_get_full_text(self, query):
        driver = webdriver.Chrome(options=self.chrome_options)
        try:
            driver.get(f"{self.base_url}?q={query}")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "result__title"))
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")
            results = []

            for result in soup.select(".result")[: self.max_results]:
                title = result.select_one(".result__title")
                link = result.select_one(".result__url")
                snippet = result.select_one(".result__snippet")

                if link and link.get("href"):
                    full_text = await self._get_full_text(driver, link["href"])
                    results.append(
                        {
                            "title": title.text.strip() if title else "",
                            "link": link["href"],
                            "snippet": snippet.text.strip() if snippet else "",
                            "full_text": full_text,
                        }
                    )

            return results
        finally:
            driver.quit()

    async def _get_full_text(self, driver, url):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Scroll to load lazy-loaded content
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Try to find the main content
            content = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_="content")
            )
            if not content:
                content = soup.find("body")

            if content:
                # Remove script and style elements
                for script in content(["script", "style"]):
                    script.decompose()
                return " ".join(content.stripped_strings)
            else:
                return "Could not extract meaningful content"
        except Exception as e:
            return f"Error fetching full text: {str(e)}"

    async def quick_search(self, query):
        return await self._search_and_get_full_text(query)


async def main():
    searcher = AdvancedSearchTool()
    query = "What is happening today in Palestine?"
    results = await searcher.quick_search(query)
    for result in results:
        print("Title:", result["title"])
        print("Link:", result["link"])
        print("Snippet:", result["snippet"])
        print(
            "Full Text (preview):",
            (
                result["full_text"][:500] + "..."
                if len(result["full_text"]) > 500
                else result["full_text"]
            ),
        )
        print("---")


if __name__ == "__main__":
    asyncio.run(main())
