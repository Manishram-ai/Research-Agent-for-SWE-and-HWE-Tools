import os
from dotenv import load_dotenv
from firecrawl import Firecrawl
from firecrawl.types import ScrapeOptions

load_dotenv()

class FirecrawlService:
    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("Missing FIRECRAWL_API_KEY environment variable")
        self.app = Firecrawl(api_key=api_key)

    def search_companies(self, query: str, num_results: int = 5):
        
        try:
            # Include scrape_options to get page content for each result (e.g., markdown)
            # Include scrape_options to get page content for each result (e.g., markdown)
            result = self.app.search(
                query=f"{query}  and company pricing official website",
                limit=num_results,
            )
            return result
        except Exception as e:
            print(e)
            return []

    def scrape_company_pages(self, url: str):
        print(url)
        print(f"About to scrape: {url!r}")  
        try:
            # Use v2 scrape API
            result = self.app.scrape(
                url,
                formats=["markdown"]
            )
            return result
        except Exception as e:
            print(e)
            return None
