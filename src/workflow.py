from typing import List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.models import * 
from src.firecrawl_client import FirecrawlService
from src.prompts import DeveloperToolsPrompts



class Workflow:
    def __init__(self):
        self.firecrawl_service = FirecrawlService()
        self.llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.4)
        self.prompts = DeveloperToolsPrompts()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        # extract tools from articles and looking at the website 
        # research those tools based on the tools that are extracted
        # analyze the tools and give a summary of the tools
        # generate recommendations
        
        graph = StateGraph(ResearchState)
        
        graph.add_node("extract_tools", self._extract_tools)
        graph.add_node("research", self._research_step)
        graph.add_node("recommendation", self._recommendation_step)
        
        graph.set_entry_point("extract_tools")
        
        graph.add_edge("extract_tools", "research")
        graph.add_edge("research", "recommendation")
        graph.add_edge("recommendation", END)
        
        return graph.compile()
    # using search go to the url and scrap it, pass it to the llm to extract only the tools and return and update the state with the tools
    def _extract_tools(self, state: ResearchState) -> Dict[str, Any]:
        print(f" 🔍 Finding tools from articles and website about {state.query}")
        
        article_query = f"{state.query} tools and comparison and the best alternatives"
        search_results = self.firecrawl_service.search_companies(article_query, num_results=5)
        all_content = ""

        # Normalize search results → list of items
        if isinstance(search_results, list):
            web_items = search_results
            print('this is a list')
        elif isinstance(search_results, dict):
            web_items = search_results.get("web") or search_results.get("data") or []
            print('this is a dict')
        else:
            web_items = getattr(search_results, "web", []) or []
            print('this is a object')
        unsupported = ("reddit.com", "redd.it", "linkedin.com", "x.com", "twitter.com", "youtube.com", "tiktok.com")
        for item in web_items or []:
            # url
            url = (
                (item.get("url") if isinstance(item, dict) else getattr(item, "url", None))
                or (item.get("link") if isinstance(item, dict) else None)
            )
            if not url or any(d in url for d in unsupported):
                continue

            # Prefer content from search result
            if isinstance(item, dict):
                item_md = item.get("markdown") or item.get("content") or item.get("snippet") or item.get("description") or ""
                print('this is a markdown dict')
            else:
                item_md = (getattr(item, "markdown", None) or getattr(item, "description", None) or "") 
                print('this is a markdown object')

            if item_md.strip():
                all_content += item_md[:1500] + "\n\n"
                continue

            # Fallback: scrape the page
            scraped_content = self.firecrawl_service.scrape_company_pages(url)

            md = None
            if isinstance(scraped_content, dict):
                md = scraped_content.get("markdown")
                if not md:
                    data = scraped_content.get("data")
                    if isinstance(data, list) and data and isinstance(data[0], dict):
                        md = data[0].get("markdown") or data[0].get("content")
            else:
                md = getattr(scraped_content, "markdown", None)

            if md:
                all_content += md[:1500] + "\n\n" # scrape the page with the url
                
                
        if all_content.strip() == "":
            print(" ⚠️ No article content scraped; skipping tool extraction.")
            print(all_content)
            return {"extracted_tools": []}

        messages = [
            SystemMessage(content=self.prompts.TOOL_EXTRACTION_SYSTEM),
            HumanMessage(content=self.prompts.tool_extraction_user(state.query, all_content))
        ]
        
        try:
            response = self.llm.invoke(messages)
            tool_names = [name.strip() for name in response.content.split("\n") if name.strip()]
            
            print(f" 🛠️ Extracted tools: {', '.join(tool_names[:5])}") 
            return {"extracted_tools": tool_names}
        except Exception as e:
            print(f" 🚨 Error extracting tools: {e}")
            return {"extracted_tools": []}
        
        
    def _analyze_company_content(self, company_name: str, content: str)-> CompanyAnalysis:
            structured_llm = self.llm.with_structured_output(CompanyAnalysis) # this is a helper function to analyze the content of the company
            
            messages = [
                SystemMessage(content=self.prompts.TOOL_ANALYSIS_SYSTEM),
                HumanMessage(content= self.prompts.tool_analysis_user(company_name, content))
            ]
            
            try:
                analysis = structured_llm.invoke(messages)
                return analysis
            except Exception as e:
                print(f" 🚨 Error analyzing company content: {e}")
                return CompanyAnalysis(
                    pricing_model="Unknown",
                    is_open_source=None,
                    tech_stack=[],
                    description="Unknown",
                    api_available=None,
                    language_support=[],
                    integration_capabilities=[]
                )
                
                
    def _research_step(self, state: ResearchState) -> dict[str, Any]:
        extracted_tools = getattr(state, "extracted_tools", [])

        if not extracted_tools:
            print(" ⚠️ No extracted tools found, falling back to search")
            sr = self.firecrawl_service.search_companies(state.query, num_results=4)

            # Support both typed and dict-style SDK returns
            web_items = getattr(sr, "web", None)
            if web_items is None and isinstance(sr, dict):
                web_items = sr.get("web", [])

            tool_names: list[str] = []
            for item in web_items or []:
                title = getattr(item, "title", None) if not isinstance(item, dict) else item.get("title")
                if title:
                    tool_names.append(title)
            if not tool_names:
                tool_names = ["Unknown"]
        else:
            tool_names = extracted_tools[:4]
            print(f"🔬 Researching specific tools: {', '.join(tool_names)}")

        companies: list[CompanyInfo] = []

        for tool_name in tool_names:
            tool_sr = self.firecrawl_service.search_companies(f"{tool_name} official website", num_results=1)

            url, desc = None, ""
            if tool_sr:
                items = getattr(tool_sr, "web", None)
                if items is None and isinstance(tool_sr, dict):
                    items = tool_sr.get("web", [])
                if items:
                    first = items[0]
                    url = getattr(first, "url", None) if not isinstance(first, dict) else first.get("url")
                    # Prefer markdown if search was run with scrape_options; else use description
                    desc = (
                        (getattr(first, "markdown", None) if not isinstance(first, dict) else first.get("markdown"))
                        or (getattr(first, "description", None) if not isinstance(first, dict) else first.get("description"))
                        or ""
                    )

            # Create the CompanyInfo early so downstream code can enrich it
            company = CompanyInfo(
                name=tool_name,
                description=desc,
                website=url or "",
                tech_stack=[],
                competitors=[],
            )

            if url:
                scraped = self.firecrawl_service.scrape_company_pages(url)
                if scraped and getattr(scraped, "markdown", None):
                    content = scraped.markdown
                    analysis = self._analyze_company_content(company.name, content)  # CALLER
                    company.is_open_source = analysis.is_open_source
                    company.pricing_model = analysis.pricing_model
                    company.description = analysis.description or company.description
                    company.api_available = analysis.api_available
                    company.tech_stack = analysis.tech_stack
                    company.language_support = analysis.language_support
                    company.integration_capabilities = analysis.integration_capabilities

            companies.append(company)

        return {"company_info": companies}

             
            
    def _recommendation_step(self, state: ResearchState) -> Dict[str, Any]:
            print(' 🤖 Generating recommendations...')
            
            
            company_data = ", ".join([company.json() for company in state.company_info])
            
            messages = [
                SystemMessage(content=self.prompts.RECOMMENDATIONS_SYSTEM),
                HumanMessage(content=self.prompts.recommendations_user(state.query, company_data))
            ]
            
            response = self.llm.invoke(messages)
            return {"analysis": response.content}
        
        
    
    def run(self, query: str) -> ResearchState:
        initial_state = ResearchState(query=query)
        final_state = self.workflow.invoke(initial_state)
        return ResearchState(**final_state)
    
        
        
        
