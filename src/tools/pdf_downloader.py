# AIDEV-SECTION: PDF Download Tool for Open Access Papers
"""
PDF download functionality for open-access papers.
Supports PMC, bioRxiv, medRxiv, arXiv, and PLOS.
"""
import logging
import httpx
from typing import Optional, Dict, Any
import PyPDF2
import io

logger = logging.getLogger(__name__)

async def download_pdf_content(url: str, timeout: int = 30) -> Optional[str]:
    """
    Download and extract text from a PDF URL.
    
    Args:
        url: Direct URL to PDF file
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text content or None if failed
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, follow_redirects=True)
            
            if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/pdf'):
                # Extract text from PDF
                pdf_file = io.BytesIO(response.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                text_content = []
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content.append(page.extract_text())
                
                full_text = "\n\n".join(text_content)
                logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
                return full_text
            else:
                logger.warning(f"Failed to download PDF from {url}: Status {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Error downloading PDF from {url}: {e}")
        return None

async def get_open_access_pdf_url(paper: Dict[str, Any]) -> Optional[str]:
    """
    Determine if a paper has an open-access PDF and return its URL.
    
    Args:
        paper: Paper metadata dictionary
        
    Returns:
        PDF URL if available, None otherwise
    """
    # Check for PMC papers
    if pmcid := paper.get("pmcid"):
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
    
    # Check for bioRxiv/medRxiv
    url = paper.get("url", "")
    if "biorxiv.org" in url:
        # Convert HTML URL to PDF URL
        return url.replace("/content/", "/content/").split("v")[0] + ".full.pdf"
    elif "medrxiv.org" in url:
        return url.replace("/content/", "/content/").split("v")[0] + ".full.pdf"
    
    # Check for arXiv
    if "arxiv.org" in url:
        if "/abs/" in url:
            arxiv_id = url.split("/abs/")[1]
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    
    # Check for PLOS
    if "plos.org" in url and paper.get("isOpenAccess"):
        # PLOS provides PDFs at predictable URLs
        return url.replace("/article?", "/article/file?") + "&type=printable"
    
    # Check if paper metadata indicates open access with PDF link
    if paper.get("isOpenAccess") and (pdf_url := paper.get("pdf_url")):
        return pdf_url
    
    return None

async def fetch_full_text_if_available(paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance paper metadata with full-text content if available.
    
    Args:
        paper: Paper metadata dictionary
        
    Returns:
        Enhanced paper dict with 'full_text' field if PDF was accessible
    """
    paper_copy = paper.copy()
    
    if pdf_url := await get_open_access_pdf_url(paper):
        logger.info(f"Attempting to download PDF for: {paper.get('title', 'Unknown')}")
        
        if full_text := await download_pdf_content(pdf_url):
            paper_copy["full_text"] = full_text
            paper_copy["pdf_url"] = pdf_url
            paper_copy["has_full_text"] = True
            logger.info(f"Successfully added full text for paper: {paper.get('title', 'Unknown')}")
        else:
            paper_copy["has_full_text"] = False
            paper_copy["pdf_attempted"] = True
    else:
        paper_copy["has_full_text"] = False
        paper_copy["open_access"] = False
    
    return paper_copy