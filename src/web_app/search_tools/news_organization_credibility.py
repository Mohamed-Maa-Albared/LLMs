import json
import re
from difflib import get_close_matches
from typing import Any, Dict, List, Optional

from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate


class NewsOrganizationAnalyzer:
    """
    A class to analyze and retrieve information about news organizations,
    and match links to organizations using a local LLM with batch processing.

    This class provides methods to load news organization data from a JSON file,
    list all organizations, retrieve detailed information about specific organizations,
    and match multiple links to organizations using Ollama and LangChain in a single call.

    Attributes:
        _data (List[Dict[str, Any]]): The loaded news organization data.
        _org_names (List[str]): A list of all news organization names.
        llm (Ollama): The Ollama language model for link matching.
        prompt (PromptTemplate): The prompt template for the LLM.
    """

    def __init__(
        self,
        json_file_path: str = "src/web_app/search_tools/news_credibility/source_information.json",
    ):
        """
        Initialize the NewsOrganizationAnalyzer with data from a JSON file and set up the LLM.

        Args:
            json_file_path (str): Path to the JSON file containing news organization data.
        """
        self._data: List[Dict[str, Any]] = []
        self._org_names: List[str] = []
        self._load_data(json_file_path)

        # Set up Ollama LLM and LangChain cache
        self.llm = Ollama(model="llama3.2")
        set_llm_cache(InMemoryCache())
        self.prompt = PromptTemplate(
            input_variables=["links", "org_list"],
            template="""Match these links to news organizations:
                        Links: {links}
                        Organizations: {org_list}

                        RULES:
                        1. For each link, pick **ONE matching organization as written exactly in the list or use 'unmatched'**
                        2. Use **EXACT organization names from the list**
                        3. Include all input links
                        4. No explanations or extra text, just the JSON, Where every key is a link and every value is a matching organization name or 'unmatched'
                        Example:
                        {{"https://www.bbc.com": "BBC (British Broadcasting Corporation)", "https://example.com": "unmatched"}}

            """,
        )

    def _load_data(self, json_file_path: str) -> None:
        """
        Load news organization data from a JSON file.

        Args:
            json_file_path (str): Path to the JSON file containing news organization data.
        """
        with open(json_file_path, "r") as file:
            data = json.load(file)
        self._data = data["news_sources"]
        self._org_names = sorted(source["name"] for source in self._data)

    def list_organizations(self) -> str:
        """
        Get a formatted list of all news organizations.

        Returns:
            str: A numbered list of all news organizations.
        """
        return "\n".join(f"{i+1}. {name}" for i, name in enumerate(self._org_names))

    def get_organization_info(self, org_name: str) -> str:
        """
        Get detailed information about a specific news organization.

        Args:
            org_name (str): The name of the news organization to search for.

        Returns:
            str: Formatted information about the news organization, or an error message if not found.
        """
        closest_match = self._find_closest_match(org_name)

        if not closest_match:
            return f"No close match found for '{org_name}'"

        org_data = next(
            source for source in self._data if source["name"] == closest_match
        )

        return self._format_org_info(closest_match, org_data)

    def _format_org_info(self, org_name: str, org_data: Dict[str, Any]) -> str:
        """
        Format the information of a news organization.

        Args:
            org_name (str): The name of the news organization.
            org_data (Dict[str, Any]): The data of the news organization.

        Returns:
            str: Formatted information about the news organization.
        """
        info = [f"Information for {org_name}:\n"]

        for key, value in org_data.items():
            info.append(f"{key.replace('_', ' ').title()}:")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    info.append(f"  {sub_key.replace('_', ' ').title()}: {sub_value}")
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        info.append(f"  - {item}")
                    elif isinstance(item, dict):
                        for sub_key, sub_value in item.items():
                            info.append(
                                f"  - {sub_key.replace('_', ' ').title()}: {sub_value}"
                            )
            else:
                info.append(f"  {value}")
            info.append("")

        return "\n".join(info).strip()

    def match_links_to_orgs(self, links: List[str]) -> Dict[str, str]:
        """
        Match a list of links to news organizations using the LLM in a single batch.

        Args:
            links (List[str]): A list of URLs to match to news organizations.

        Returns:
            Dict[str, str]: A dictionary mapping links to matched organization names.
        """
        org_list = "\n".join(self._org_names)
        links_str = "\n".join(links)

        try:
            llm_output = self.llm(
                self.prompt.format(links=links_str, org_list=org_list)
            )
            llm_output = self._clean_json_string(llm_output)
            matches = json.loads(llm_output)

            # Clean up the matches
            cleaned_matches = []
            for _, org in matches.items():
                if org.lower() != "unmatched":
                    closest_match = self._find_closest_match(org)
                    if closest_match:
                        cleaned_matches.append(closest_match)
            cleaned_matches = list(set(cleaned_matches))
            return cleaned_matches
        except Exception as e:
            print(f"Error processing links: {str(e)}")
            return {}

    def _clean_json_string(self, json_str):
        # Remove invalid escape characters
        json_str = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"", json_str)
        return json_str

    def _find_closest_match(self, org_name: str) -> str:
        """
        Find the closest matching organization name from the loaded data.

        Args:
            org_name (str): The name to match against the loaded organization names.

        Returns:
            str: The closest matching organization name, or an empty string if no match is found.
        """
        matches = get_close_matches(org_name, self._org_names, n=1, cutoff=0.6)
        return matches[0] if matches else ""
