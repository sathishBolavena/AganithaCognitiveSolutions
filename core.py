import requests
import pandas as pd
from typing import List, Dict, Optional, Tuple
from xml.etree import ElementTree as ET
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PubMedFetcher:
    """Core class for fetching and processing PubMed papers."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    def _init_(self, email: str):
        self.email = email
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"PubMedFetcher/{email}"})
    
    def fetch_papers(self, query: str, max_results: int = 200) -> List[Dict[str, str]]:
        """Fetch papers matching query with industry affiliations."""
        try:
            pubmed_ids = self._fetch_pubmed_ids(query, max_results)
            if not pubmed_ids:
                logger.warning("No papers found matching query")
                return []
                
            papers_data = []
            for pmid in pubmed_ids:
                paper = self._process_paper(pmid)
                if paper:
                    papers_data.append(paper)
            
            return papers_data
            
        except Exception as e:
            logger.error(f"Failed to fetch papers: {e}")
            return []
    
    def _fetch_pubmed_ids(self, query: str, max_results: int) -> List[str]:
        """Fetch PubMed IDs for a query."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "email": self.email
        }
        response = self.session.get(f"{self.BASE_URL}esearch.fcgi", params=params)
        response.raise_for_status()
        return response.json().get("esearchresult", {}).get("idlist", [])
    
    def _process_paper(self, pmid: str) -> Optional[Dict[str, str]]:
        """Process individual paper details."""
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "email": self.email
        }
        response = self.session.get(f"{self.BASE_URL}efetch.fcgi", params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        article = root.find(".//PubmedArticle")
        if not article:
            return None
            
        title = self._get_text(article, ".//ArticleTitle")
        pub_date = self._get_text(article, ".//PubDate/Year") or self._get_text(article, ".//PubDate/Month")
        
        authors_info = self._process_authors(article)
        if not authors_info["industry_authors"]:
            return None
            
        return {
            "PubmedID": pmid,
            "Title": title,
            "Publication Date": pub_date,
            "Non-academic Author(s)": "; ".join(authors_info["industry_names"]),
            "Company Affiliation(s)": "; ".join(authors_info["industry_affiliations"]),
            "Corresponding Author Email": authors_info["corresponding_email"] or "N/A"
        }
    
    def _process_authors(self, article: ET.Element) -> Dict:
        """Process author information with industry detection."""
        industry_names = []
        industry_affiliations = []
        corresponding_email = ""
        
        for author in article.findall(".//Author"):
            name = self._format_author_name(author)
            affiliation = self._get_text(author, "Affiliation")
            email = self._extract_email(affiliation) if affiliation else ""
            
            if affiliation and self._is_industry_affiliation(affiliation):
                industry_names.append(name)
                industry_affiliations.append(affiliation)
                
                # Prefer corresponding author email
                if not corresponding_email and email:
                    corresponding_email = email
        
        return {
            "industry_names": industry_names,
            "industry_affiliations": industry_affiliations,
            "corresponding_email": corresponding_email
        }
    
    def _is_industry_affiliation(self, affiliation: str) -> bool:
        """Determine if affiliation is from industry."""
        affil_lower = affiliation.lower()
        
        # Academic indicators
        academic_keywords = [
            "university", "college", "institute", 
            "hospital", "school", "academy", "lab"
        ]
        if any(kw in affil_lower for kw in academic_keywords):
            return False
            
        # Industry indicators
        industry_keywords = [
            "pharma", "biotech", "inc", "ltd", 
            "corporation", "therapeutics", "vaccine",
            "genetics", "healthcare", "medical"
        ]
        return any(kw in affil_lower for kw in industry_keywords)
    
    @staticmethod
    def _format_author_name(author: ET.Element) -> str:
        """Format author name from XML elements."""
        last_name = author.find("LastName").text if author.find("LastName") is not None else ""
        fore_name = author.find("ForeName").text if author.find("ForeName") is not None else ""
        return f"{fore_name} {last_name}".strip()
    
    @staticmethod
    def _get_text(element: ET.Element, path: str) -> str:
        """Safe XML text extraction."""
        target = element.find(path)
        return target.text if target is not None else ""
    
    @staticmethod
    def _extract_email(text: str) -> str:
        """Extract email address from text."""
        match = re.search(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}', text or "")
        return match.group(0) if match else ""