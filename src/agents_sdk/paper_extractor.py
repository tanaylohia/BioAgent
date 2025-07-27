# AIDEV-SECTION: Paper Extraction from SDK Results
"""
Extract Paper objects from SDK agent outputs.
Converts string outputs back to structured Paper objects.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from agents import RunResult
from agents.items import ToolCallOutputItem
from src.models.paper import Paper

logger = logging.getLogger(__name__)


def extract_papers_from_run_result(result: RunResult) -> List[Paper]:
    """
    Extract all papers from an SDK RunResult.
    
    Args:
        result: The RunResult from SDK Runner
        
    Returns:
        List of Paper objects
    """
    all_papers = []
    
    # Iterate through all items in the result
    for item in result.new_items:
        if isinstance(item, ToolCallOutputItem):
            # Extract papers from tool outputs
            papers = extract_papers_from_tool_output(item.output)
            all_papers.extend(papers)
    
    # Deduplicate papers
    return deduplicate_papers(all_papers)


def extract_papers_from_tool_output(output: str) -> List[Paper]:
    """
    Extract Paper objects from a tool's string output.
    
    Args:
        output: String output from a tool
        
    Returns:
        List of Paper objects
    """
    papers = []
    
    try:
        # Find JSON in the output - look for RAW JSON DATA section
        if "=== RAW JSON DATA ===" in output:
            json_start = output.find("{", output.find("=== RAW JSON DATA ==="))
            if json_start > -1:
                # Find the end of JSON (before next section or end of string)
                json_end = len(output)
                json_str = output[json_start:json_end].strip()
                
                # Parse JSON
                data = json.loads(json_str)
                
                # Extract papers based on the data structure
                papers.extend(extract_papers_from_results(data))
        
    except Exception as e:
        logger.error(f"Error extracting papers from tool output: {e}")
    
    return papers


def extract_papers_from_results(data: Dict[str, Any]) -> List[Paper]:
    """
    Extract papers from various result formats.
    
    Args:
        data: Parsed JSON data from tool output
        
    Returns:
        List of Paper objects
    """
    papers = []
    
    try:
        # Handle different result formats
        if "results" in data:
            # Standard format (PubMed, Google Academic, etc.)
            for item in data.get("results", []):
                paper = create_paper_from_item(item, data.get("source", "Unknown"))
                if paper:
                    papers.append(paper)
        
        if "semantic_scholar" in data:
            # search_papers format
            for item in data.get("semantic_scholar", []):
                paper = create_paper_from_item(item, "Semantic Scholar")
                if paper:
                    papers.append(paper)
        
        if "crossref" in data:
            for item in data.get("crossref", []):
                paper = create_paper_from_item(item, "CrossRef")
                if paper:
                    papers.append(paper)
        
        if "biorxiv" in data:
            # Preprints format
            for item in data.get("biorxiv", []):
                paper = create_paper_from_item(item, "bioRxiv")
                if paper:
                    papers.append(paper)
        
        if "medrxiv" in data:
            for item in data.get("medrxiv", []):
                paper = create_paper_from_item(item, "medRxiv")
                if paper:
                    papers.append(paper)
        
        # Handle Semantic Scholar topic search format
        if "data" in data and isinstance(data["data"], list):
            for item in data["data"]:
                paper = create_paper_from_semantic_scholar(item)
                if paper:
                    papers.append(paper)
    
    except Exception as e:
        logger.error(f"Error extracting papers from results: {e}")
    
    return papers


def create_paper_from_item(item: Dict[str, Any], source: str) -> Optional[Paper]:
    """
    Create a Paper object from a result item.
    
    Args:
        item: Dictionary containing paper data
        source: Source database name
        
    Returns:
        Paper object or None if creation fails
    """
    try:
        # Extract title
        title = item.get("title") or item.get("briefTitle") or ""
        if not title:
            return None
        
        # Extract authors
        authors = extract_authors(item)
        
        # Extract abstract
        abstract = (
            item.get("abstract") or 
            item.get("summary") or 
            item.get("snippet") or 
            item.get("description") or 
            ""
        )
        
        # Extract URL
        url = (
            item.get("url") or 
            item.get("link") or 
            item.get("doi") or 
            item.get("hyperlink") or 
            ""
        )
        
        # Extract publication date
        publication_date = parse_date(
            item.get("year") or 
            item.get("date") or 
            item.get("pubYear") or 
            item.get("publication_date") or
            item.get("publicationDate")
        )
        
        # Extract other fields
        doi = item.get("doi")
        journal = item.get("journal") or item.get("venue") or item.get("source")
        citations = item.get("citations", 0)
        
        # Create Paper object
        return Paper(
            title=title,
            abstract=abstract,
            authors=authors[:10],  # Limit to 10 authors
            citations=citations,
            publication_date=publication_date,
            hyperlink=url,
            source=source,
            doi=doi,
            journal=journal
        )
    
    except Exception as e:
        logger.error(f"Error creating paper from item: {e}")
        return None


def create_paper_from_semantic_scholar(item: Dict[str, Any]) -> Optional[Paper]:
    """
    Create a Paper object from Semantic Scholar format.
    
    Args:
        item: Semantic Scholar paper data
        
    Returns:
        Paper object or None
    """
    try:
        title = item.get("title", "")
        if not title:
            return None
        
        # Extract authors from Semantic Scholar format
        authors = []
        for author in item.get("authors", []):
            if isinstance(author, dict):
                name = author.get("name", "")
                if name:
                    authors.append(name)
        
        # Extract other fields
        abstract = item.get("abstract", "")
        year = item.get("year")
        publication_date = parse_date(year)
        
        # Build URL
        paper_id = item.get("paperId")
        url = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""
        
        return Paper(
            title=title,
            abstract=abstract,
            authors=authors[:10],
            citations=item.get("citationCount", 0),
            publication_date=publication_date,
            hyperlink=url,
            source="Semantic Scholar",
            doi=item.get("doi"),
            journal=item.get("venue")
        )
    
    except Exception as e:
        logger.error(f"Error creating paper from Semantic Scholar: {e}")
        return None


def extract_authors(item: Dict[str, Any]) -> List[str]:
    """Extract authors from various formats"""
    authors = item.get("authors", [])
    
    if isinstance(authors, str):
        # Single author string
        return [authors]
    elif isinstance(authors, list):
        # List of authors
        result = []
        for author in authors:
            if isinstance(author, str):
                result.append(author)
            elif isinstance(author, dict):
                # Extract name from dict
                name = author.get("name") or author.get("authorName") or ""
                if name:
                    result.append(name)
        return result
    else:
        return []


def parse_date(date_value: Any) -> Optional[datetime]:
    """Parse various date formats"""
    if not date_value:
        return None
    
    try:
        if isinstance(date_value, int):
            # Year only
            return datetime(date_value, 1, 1)
        elif isinstance(date_value, str):
            # Try to extract year
            import re
            year_match = re.search(r'\d{4}', str(date_value))
            if year_match:
                return datetime(int(year_match.group()), 1, 1)
    except:
        pass
    
    return None


def deduplicate_papers(papers: List[Paper]) -> List[Paper]:
    """Remove duplicate papers based on title and DOI"""
    seen = set()
    unique = []
    
    for paper in papers:
        # Create unique key
        key = (paper.title.lower(), paper.doi) if paper.doi else paper.title.lower()
        
        if key not in seen:
            seen.add(key)
            unique.append(paper)
    
    return unique