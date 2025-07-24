# AIDEV-SECTION: Paper Parser Utility
"""
Utility to parse various paper formats into the Paper model
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.models.paper import Paper
import logging

logger = logging.getLogger(__name__)

def parse_paper_safe(data: Dict[str, Any], source: str) -> Optional[Paper]:
    """
    Safely parse paper data from various sources into Paper model
    
    Args:
        data: Raw paper data from API
        source: Source name (semantic_scholar, crossref, pubmed, etc.)
        
    Returns:
        Paper object or None if parsing fails
    """
    try:
        # Extract title
        title = data.get('title', 'No title available')
        if isinstance(title, list):
            title = title[0] if title else 'No title available'
            
        # Extract abstract (required field, provide default)
        abstract = data.get('abstract', '')
        if not abstract:
            # Try different field names
            abstract = data.get('summary', '')
            if not abstract:
                abstract = data.get('description', '')
            if not abstract:
                abstract = 'No abstract available'
                
        # Extract authors
        authors = []
        if 'authors' in data:
            author_data = data['authors']
            if isinstance(author_data, list):
                for author in author_data:
                    if isinstance(author, dict):
                        # Handle different author formats
                        name = author.get('name', '')
                        if not name:
                            # Try combining first/last name
                            first = author.get('given', author.get('first_name', ''))
                            last = author.get('family', author.get('last_name', ''))
                            if first and last:
                                name = f"{first} {last}"
                            elif last:
                                name = last
                        if name:
                            authors.append(name)
                    elif isinstance(author, str):
                        authors.append(author)
                        
        # Extract hyperlink (required field)
        hyperlink = data.get('hyperlink', '')
        if not hyperlink:
            # Try different field names
            hyperlink = data.get('url', '')
            if not hyperlink:
                hyperlink = data.get('link', '')
            if not hyperlink and 'doi' in data and data['doi']:
                hyperlink = f"https://doi.org/{data['doi']}"
            if not hyperlink:
                hyperlink = f"https://scholar.google.com/scholar?q={title[:100]}"
                
        # Extract DOI
        doi = data.get('doi')
        if doi and doi.startswith('http'):
            # Extract DOI from URL
            doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')
            
        # Extract publication date
        publication_date = None
        if 'publication_date' in data:
            try:
                publication_date = datetime.fromisoformat(data['publication_date'])
            except:
                pass
        elif 'published_date' in data:
            try:
                publication_date = datetime.fromisoformat(data['published_date'])
            except:
                pass
        elif 'year' in data:
            try:
                year = int(data['year'])
                publication_date = datetime(year, 1, 1)
            except:
                pass
                
        # Extract citations
        citations = 0
        if 'citations' in data:
            try:
                citations = int(data['citations'])
            except:
                pass
        elif 'citationCount' in data:
            try:
                citations = int(data['citationCount'])
            except:
                pass
        elif 'cited_by_count' in data:
            try:
                citations = int(data['cited_by_count'])
            except:
                pass
                
        # Extract journal
        journal = data.get('journal', data.get('venue', data.get('publisher', None)))
        
        # Create Paper object
        paper = Paper(
            title=title,
            abstract=abstract,
            authors=authors,
            citations=citations,
            publication_date=publication_date,
            hyperlink=hyperlink,
            source=source,
            doi=doi,
            journal=journal
        )
        
        return paper
        
    except Exception as e:
        logger.error(f"Failed to parse paper from {source}: {e}")
        logger.debug(f"Paper data: {data}")
        return None


def parse_papers_from_tool_response(response: Dict[str, Any], tool_name: str) -> List[Paper]:
    """
    Parse papers from various tool responses
    
    Args:
        response: Raw response from tool
        tool_name: Name of the tool that generated response
        
    Returns:
        List of Paper objects
    """
    papers = []
    
    if tool_name == "search_papers":
        # Handle semantic scholar results
        for paper_data in response.get('semantic_scholar', []):
            paper = parse_paper_safe(paper_data, 'semantic_scholar')
            if paper:
                papers.append(paper)
                
        # Handle crossref results
        for paper_data in response.get('crossref', []):
            paper = parse_paper_safe(paper_data, 'crossref')
            if paper:
                papers.append(paper)
                
    elif tool_name == "search_pubmed":
        # Handle pubmed results
        for paper_data in response.get('results', []):
            paper = parse_paper_safe(paper_data, 'pubmed')
            if paper:
                papers.append(paper)
                
    elif tool_name == "search_by_topic":
        # Handle topic search results
        for paper_data in response.get('data', []):
            paper = parse_paper_safe(paper_data, 'semantic_scholar')
            if paper:
                papers.append(paper)
                
    elif tool_name == "google_academic_search":
        # Handle google results
        for result in response.get('results', []):
            # Convert google format to standard format
            paper_data = {
                'title': result.get('title', ''),
                'abstract': result.get('snippet', ''),
                'url': result.get('link', ''),
                'authors': result.get('authors', [])
            }
            paper = parse_paper_safe(paper_data, 'google_scholar')
            if paper:
                papers.append(paper)
                
    elif tool_name == "search_preprints":
        # Handle biorxiv results
        for paper_data in response.get('biorxiv', []):
            paper = parse_paper_safe(paper_data, 'biorxiv')
            if paper:
                papers.append(paper)
                
        # Handle medrxiv results  
        for paper_data in response.get('medrxiv', []):
            paper = parse_paper_safe(paper_data, 'medrxiv')
            if paper:
                papers.append(paper)
                
    return papers