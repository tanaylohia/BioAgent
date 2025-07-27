# AIDEV-SECTION: Direct Implementation of All Search Tools
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import json
# PDF downloads disabled - abstracts are sufficient
# from .pdf_downloader import fetch_full_text_if_available, get_open_access_pdf_url

logger = logging.getLogger(__name__)

# API Endpoints
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
CROSSREF_API = "https://api.crossref.org/works"
PUBMED_API = "https://www.ebi.ac.uk/europepmc/webservices/rest"
PUBTATOR_API = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
CLINICALTRIALS_API = "https://clinicaltrials.gov/api/v2"
MYVARIANT_API = "https://myvariant.info/v1"
BIORXIV_API = "https://api.biorxiv.org/details/v1"
GOOGLE_SEARCH_API = "https://www.googleapis.com/customsearch/v1"

# AIDEV-SECTION: Academic Literature Tools

async def google_academic_search(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search Google for academic papers and scholarly articles.
    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables.
    
    Args:
        query: Search query string
        limit: Maximum number of results (max 10 per request)
        
    Returns:
        Dictionary with Google Scholar-like results
    """
    import os
    
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")  # Custom Search Engine ID
    
    if not api_key or not cse_id:
        logger.warning("Google API key or CSE ID not configured")
        return {"error": "Google Search API not configured", "results": []}
    
    # Academic search parameters optimized for biomedical content
    # Add site: operators to focus on academic sources
    academic_query = f"{query} (site:pubmed.ncbi.nlm.nih.gov OR site:nature.com OR site:science.org OR site:cell.com OR site:nejm.org OR site:arxiv.org OR site:biorxiv.org OR site:plos.org OR site:sciencedirect.com)"
    
    academic_params = {
        "key": api_key,
        "cx": cse_id,
        "q": academic_query,
        "num": min(limit, 10),  # Google limits to 10 results per request
        "lr": "lang_en",  # Language restriction to English
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(GOOGLE_SEARCH_API, params=academic_params)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get("items", []):
                    # Extract metadata from the search result
                    result = {
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("displayLink", ""),
                        "type": "academic_search"
                    }
                    
                    # Try to extract additional metadata from pagemap if available
                    pagemap = item.get("pagemap", {})
                    metatags = pagemap.get("metatags", [{}])[0]
                    
                    # Extract authors if available
                    if "citation_author" in metatags:
                        result["authors"] = [metatags.get("citation_author")]
                    elif "author" in metatags:
                        result["authors"] = [metatags.get("author")]
                    
                    # Extract publication date
                    if "citation_publication_date" in metatags:
                        result["publication_date"] = metatags.get("citation_publication_date")
                    elif "citation_date" in metatags:
                        result["publication_date"] = metatags.get("citation_date")
                    
                    # Extract DOI if available
                    if "citation_doi" in metatags:
                        result["doi"] = metatags.get("citation_doi")
                    
                    # Extract journal/venue
                    if "citation_journal_title" in metatags:
                        result["journal"] = metatags.get("citation_journal_title")
                    
                    results.append(result)
                
                return {
                    "results": results,
                    "total_results": data.get("searchInformation", {}).get("totalResults", 0),
                    "search_time": data.get("searchInformation", {}).get("searchTime", 0)
                }
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Google Search API error: {error_msg}")
                return {"error": error_msg, "results": []}
                
        except Exception as e:
            logger.error(f"Google Academic Search error: {e}")
            return {"error": str(e), "results": []}

async def search_papers(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for academic papers using Semantic Scholar and CrossRef.
    
    Args:
        query: Search query string
        limit: Maximum number of results per source
        
    Returns:
        Dictionary with results from both sources
    """
    # Use shorter timeouts for individual requests
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        results = {"semantic_scholar": [], "crossref": [], "total": 0}
        
        # Search Semantic Scholar with retry logic
        try:
            # Retry logic for rate limiting
            for attempt in range(3):
                ss_response = await client.get(
                    f"{SEMANTIC_SCHOLAR_API}/paper/search",
                    params={
                        "query": query, 
                        "limit": limit,
                        "fields": "title,authors,year,abstract,venue,isOpenAccess,tldr,externalIds,citationCount"
                    }
                )
                
                if ss_response.status_code == 429:
                    if attempt < 2:  # Don't sleep on last attempt
                        logger.warning(f"Semantic Scholar rate limited, retrying in {2 ** attempt} seconds...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                        continue
                    else:
                        logger.warning("Semantic Scholar rate limited after retries, skipping...")
                        results["semantic_scholar"] = []
                        break
                elif ss_response.status_code == 200:
                    data = ss_response.json()
                    for paper in data.get("data", []):
                        results["semantic_scholar"].append({
                            "title": paper.get("title"),
                        "authors": [a.get("name") for a in paper.get("authors", [])],
                        "year": paper.get("year"),
                        "abstract": paper.get("abstract"),
                        "doi": paper.get("externalIds", {}).get("DOI"),
                        "url": paper.get("url"),
                        "venue": paper.get("venue"),
                        "openAccess": paper.get("isOpenAccess"),
                        "tldr": paper.get("tldr", {}).get("text") if paper.get("tldr") else None
                    })
                    break  # Success, exit retry loop
                else:
                    logger.error(f"Semantic Scholar unexpected status: {ss_response.status_code}")
                    break
        except Exception as e:
            logger.error(f"Semantic Scholar error: {e}")
        
        # Search CrossRef
        try:
            cr_response = await client.get(
                CROSSREF_API,
                params={"query": query, "rows": limit}
            )
            if cr_response.status_code == 200:
                data = cr_response.json()
                for item in data.get("message", {}).get("items", []):
                    results["crossref"].append({
                        "title": item.get("title", [""])[0] if item.get("title") else "",
                        "authors": [
                            f"{a.get('given', '')} {a.get('family', '')}".strip()
                            for a in item.get("author", [])
                        ],
                        "year": item.get("published-print", {}).get("date-parts", [[None]])[0][0],
                        "doi": item.get("DOI"),
                        "url": item.get("URL"),
                        "publisher": item.get("publisher"),
                        "type": item.get("type")
                    })
        except Exception as e:
            logger.error(f"CrossRef error: {e}")
        
        results["total"] = len(results["semantic_scholar"]) + len(results["crossref"])
        return results

async def fetch_paper_details(paper_id: str, source: str = "semantic_scholar") -> Dict[str, Any]:
    """
    Get detailed information about a specific paper.
    
    Args:
        paper_id: Paper identifier (DOI or Semantic Scholar ID)
        source: Either "semantic_scholar" or "crossref"
        
    Returns:
        Detailed paper information
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if source == "semantic_scholar":
                response = await client.get(f"{SEMANTIC_SCHOLAR_API}/paper/{paper_id}")
            else:  # crossref
                response = await client.get(f"{CROSSREF_API}/{paper_id}")
            
            if response.status_code == 200:
                data = response.json()
                if source == "crossref":
                    data = data.get("message", data)
                return data
            else:
                return {"error": f"Paper not found: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

async def search_by_topic(topic: str, year_start: Optional[int] = None, 
                         year_end: Optional[int] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Search papers by topic with optional date range.
    
    Args:
        topic: Search topic (max 300 chars)
        year_start: Optional start year
        year_end: Optional end year
        limit: Maximum results
        
    Returns:
        Search results with date filtering
    """
    # Truncate long queries
    if len(topic) > 300:
        topic = topic[:300] + "..."
    
    params = {
        "query": topic,
        "limit": limit,
        "fields": "title,authors,year,abstract,venue,isOpenAccess,tldr,externalIds"
    }
    
    if year_start and year_end:
        params["year"] = f"{year_start}-{year_end}"
    elif year_start:
        params["year"] = f"{year_start}-"
    elif year_end:
        params["year"] = f"-{year_end}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Retry logic for rate limiting
            for attempt in range(3):
                response = await client.get(f"{SEMANTIC_SCHOLAR_API}/paper/search", params=params)
                
                if response.status_code == 429:
                    if attempt < 2:
                        logger.warning(f"Search by topic rate limited, retrying in {2 ** attempt} seconds...")
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        return {"error": "Rate limited after retries", "data": []}
                elif response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Search failed: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

# AIDEV-SECTION: OpenAlex - Primary Academic Search (Best Abstracts)

async def search_openalex(query: str, limit: int = 50, open_access_only: bool = False) -> Dict[str, Any]:
    """
    Search OpenAlex for academic papers with full abstracts.
    OpenAlex is the successor to Microsoft Academic and provides excellent abstract coverage.
    
    Args:
        query: Search query
        limit: Maximum results (up to 200 per request)
        open_access_only: Filter for only open access papers
        
    Returns:
        OpenAlex search results with abstracts
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            params = {
                "search": query,
                "per-page": min(limit, 200),  # OpenAlex allows up to 200 per request
                "select": "id,title,display_name,abstract_inverted_index,authorships,publication_date,doi,open_access,cited_by_count,primary_location,concepts",
                "sort": "cited_by_count:desc"  # Sort by most cited first
            }
            
            if open_access_only:
                params["filter"] = "open_access.is_oa:true"
            
            response = await client.get("https://api.openalex.org/works", params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for work in data.get("results", []):
                    # Reconstruct abstract from inverted index
                    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
                    
                    # Extract authors
                    authors = []
                    for authorship in work.get("authorships", [])[:10]:  # Limit to first 10 authors
                        author = authorship.get("author", {})
                        if author.get("display_name"):
                            authors.append(author["display_name"])
                    
                    # Extract venue information
                    venue = ""
                    location = work.get("primary_location", {})
                    if location.get("source", {}).get("display_name"):
                        venue = location["source"]["display_name"]
                    
                    paper = {
                        "title": work.get("display_name", ""),
                        "abstract": abstract,
                        "authors": authors,
                        "year": work.get("publication_date", "").split("-")[0] if work.get("publication_date") else None,
                        "doi": work.get("doi", "").replace("https://doi.org/", "") if work.get("doi") else None,
                        "url": f"https://openalex.org/{work.get('id', '').split('/')[-1]}" if work.get("id") else "",
                        "venue": venue,
                        "citations": work.get("cited_by_count", 0),
                        "openAccess": work.get("open_access", {}).get("is_oa", False),
                        "source": "OpenAlex"
                    }
                    
                    results.append(paper)
                
                return {"results": results, "total": len(results)}
            else:
                return {"error": f"OpenAlex search failed: {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e), "results": []}

def _reconstruct_abstract(inverted_index: Dict[str, List[int]]) -> str:
    """
    Reconstruct abstract text from OpenAlex inverted index format.
    
    Args:
        inverted_index: Dictionary mapping words to position lists
        
    Returns:
        Reconstructed abstract text
    """
    if not inverted_index:
        return ""
    
    try:
        # Create position to word mapping
        position_to_word = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                position_to_word[pos] = word
        
        # Sort by position and join
        sorted_positions = sorted(position_to_word.keys())
        abstract_words = [position_to_word[pos] for pos in sorted_positions]
        
        return " ".join(abstract_words)
    except Exception:
        return ""

# AIDEV-SECTION: Direct PubMed E-utilities (Official NCBI API)

async def search_pubmed_direct(query: str, limit: int = 20, include_abstracts: bool = True) -> Dict[str, Any]:
    """
    Search PubMed directly using NCBI E-utilities for better abstract retrieval.
    This bypasses Europe PMC and uses the official NCBI API.
    
    Args:
        query: Search query
        limit: Maximum results
        include_abstracts: Whether to fetch full abstracts (slower but better)
        
    Returns:
        PubMed search results with abstracts
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Step 1: Search for PMIDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": limit,
                "retmode": "json",
                "sort": "relevance"
            }
            
            search_response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params=search_params
            )
            
            if search_response.status_code != 200:
                return {"error": f"PubMed search failed: {search_response.status_code}"}
            
            search_data = search_response.json()
            pmids = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                return {"results": [], "total": 0}
            
            results = []
            
            if include_abstracts and pmids:
                # Step 2: Fetch detailed records with abstracts
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "rettype": "abstract",
                    "retmode": "xml"
                }
                
                fetch_response = await client.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                    params=fetch_params
                )
                
                if fetch_response.status_code == 200:
                    # Parse XML response
                    import xml.etree.ElementTree as ET
                    try:
                        root = ET.fromstring(fetch_response.content)
                        
                        for article in root.findall(".//PubmedArticle"):
                            paper = _parse_pubmed_article(article)
                            if paper:
                                results.append(paper)
                                
                    except ET.ParseError as e:
                        logger.error(f"XML parsing error: {e}")
                        return {"error": f"XML parsing failed: {e}"}
            
            return {"results": results, "total": len(results)}
            
        except Exception as e:
            logger.error(f"PubMed direct search error: {e}")
            return {"error": str(e), "results": []}

def _parse_pubmed_article(article_elem) -> Dict[str, Any]:
    """Parse a single PubMed article from XML"""
    try:
        # Extract PMID
        pmid_elem = article_elem.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""
        
        # Extract title
        title_elem = article_elem.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else ""
        
        # Extract abstract
        abstract_parts = []
        abstract_elem = article_elem.find(".//Abstract")
        if abstract_elem is not None:
            for text_elem in abstract_elem.findall(".//AbstractText"):
                text = text_elem.text or ""
                label = text_elem.get("Label", "")
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
        
        abstract = " ".join(abstract_parts) if abstract_parts else ""
        
        # Extract authors
        authors = []
        author_list = article_elem.find(".//AuthorList")
        if author_list is not None:
            for author in author_list.findall(".//Author")[:10]:  # Limit to 10 authors
                lastname = author.find(".//LastName")
                forename = author.find(".//ForeName")
                if lastname is not None:
                    name = lastname.text
                    if forename is not None:
                        name = f"{forename.text} {name}"
                    authors.append(name)
        
        # Extract journal and year
        journal_elem = article_elem.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""
        
        pub_date = article_elem.find(".//PubDate/Year")
        year = pub_date.text if pub_date is not None else ""
        
        # Extract DOI
        doi = ""
        for id_elem in article_elem.findall(".//ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text
                break
        
        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "year": year,
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            "source": "PubMed Direct"
        }
        
    except Exception as e:
        logger.error(f"Error parsing PubMed article: {e}")
        return None

# AIDEV-SECTION: PubMed and Preprint Tools (Legacy - Keep for backup)

async def search_pubmed(query: str, genes: List[str] = None, diseases: List[str] = None, 
                       limit: int = 20) -> Dict[str, Any]:
    """
    Search PubMed/PubTator3 for biomedical literature.
    
    Args:
        query: Main search query
        genes: List of gene names to filter
        diseases: List of diseases to filter
        limit: Maximum results
        
    Returns:
        PubMed search results with annotations
    """
    # Build query
    query_parts = []
    if query:
        query_parts.append(query)
    if genes:
        query_parts.extend([f"{gene}[Gene]" for gene in genes])
    if diseases:
        query_parts.extend([f"{disease}[Disease]" for disease in diseases])
    
    final_query = " AND ".join(query_parts) if query_parts else "*"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Using Europe PMC as proxy for PubMed
            response = await client.get(
                f"{PUBMED_API}/search",
                params={
                    "query": final_query,
                    "format": "json",
                    "pageSize": limit
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for article in data.get("resultList", {}).get("result", []):
                    paper = {
                        "pmid": article.get("pmid"),
                        "pmcid": article.get("pmcid"),  # Add PMC ID for PDF access
                        "title": article.get("title"),
                        "authors": article.get("authorString"),
                        "abstract": article.get("abstractText"),
                        "journal": article.get("journalTitle"),
                        "year": article.get("pubYear"),
                        "doi": article.get("doi"),
                        "isOpenAccess": article.get("isOpenAccess") == "Y",
                        "source": "PubMed"
                    }
                    
                    # AIDEV-NOTE: PDF downloads disabled - abstracts provide sufficient information
                    # Full text parsing can be done if already available in the response
                    
                    results.append(paper)
                return {"results": results, "total": len(results)}
            else:
                return {"error": f"PubMed search failed: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

async def search_preprints(query: str, include_biorxiv: bool = True, 
                          include_medrxiv: bool = True, limit: int = 20) -> Dict[str, Any]:
    """
    Search bioRxiv and medRxiv preprint servers.
    Note: bioRxiv API doesn't support text search, so we fetch recent papers
    and filter client-side.
    
    Args:
        query: Search query (used for filtering)
        include_biorxiv: Search bioRxiv
        include_medrxiv: Search medRxiv
        limit: Maximum results
        
    Returns:
        Preprint search results
    """
    results = {"biorxiv": [], "medrxiv": [], "total": 0}
    
    # Since bioRxiv doesn't have search, we'll fetch recent papers
    # and filter by query terms
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        servers = []
        if include_biorxiv:
            servers.append("biorxiv")
        if include_medrxiv:
            servers.append("medrxiv")
        
        for server in servers:
            try:
                # bioRxiv API: fetch recent papers from last 30 days
                response = await client.get(
                    f"https://api.biorxiv.org/details/{server}/{start_date}/{end_date}/0/json"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    query_lower = query.lower()
                    
                    # Filter results based on query
                    for article in data.get("collection", []):
                        title = article.get("title", "").lower()
                        abstract = article.get("abstract", "").lower()
                        
                        # Simple keyword matching
                        if query_lower in title or query_lower in abstract:
                            paper = {
                                "title": article.get("title"),
                                "authors": article.get("authors"),
                                "abstract": article.get("abstract"),
                                "doi": article.get("doi"),
                                "date": article.get("date"),
                                "category": article.get("category"),
                                "url": f"https://www.{server}.org/content/{article.get('doi')}" if article.get('doi') else None,
                                "source": server,
                                "isOpenAccess": True  # All preprints are open access
                            }
                            
                            # AIDEV-NOTE: PDF downloads disabled - abstracts are sufficient
                            # Preprints already include full abstracts in the response
                            
                            results[server].append(paper)
                            
                            # Stop if we have enough results
                            if len(results[server]) >= limit:
                                break
                                
            except Exception as e:
                logger.error(f"{server} search error: {e}")
    
    results["total"] = len(results["biorxiv"]) + len(results["medrxiv"])
    return results

# AIDEV-SECTION: Clinical Trials Tool

async def search_clinical_trials(condition: str = None, intervention: str = None,
                                phase: str = None, status: str = None, limit: int = 20) -> Dict[str, Any]:
    """
    Search ClinicalTrials.gov for clinical trials.
    
    Args:
        condition: Medical condition being studied
        intervention: Treatment intervention (drug, procedure, etc.)
        phase: Trial phase (e.g., "3", "2|3")
        status: Trial status (e.g., "RECRUITING")
        limit: Maximum results
        
    Returns:
        Clinical trial search results
    """
    params = {
        "format": "json",
        "pageSize": limit
    }
    
    # Build query expression
    query_parts = []
    if condition:
        query_parts.append(f"AREA[Condition]({condition})")
    if intervention:
        query_parts.append(f"AREA[Intervention]({intervention})")
    if phase:
        query_parts.append(f"AREA[Phase]({phase})")
    if status:
        query_parts.append(f"AREA[OverallStatus]({status})")
    
    if query_parts:
        params["query.cond"] = " AND ".join(query_parts)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{CLINICALTRIALS_API}/studies", params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for study in data.get("studies", []):
                    protocol = study.get("protocolSection", {})
                    id_module = protocol.get("identificationModule", {})
                    status_module = protocol.get("statusModule", {})
                    desc_module = protocol.get("descriptionModule", {})
                    
                    results.append({
                        "nctId": id_module.get("nctId"),
                        "title": id_module.get("briefTitle"),
                        "status": status_module.get("overallStatus"),
                        "phase": status_module.get("phases", []),
                        "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
                        "interventions": [
                            i.get("name") for i in 
                            protocol.get("armsInterventionsModule", {}).get("interventions", [])
                        ],
                        "summary": desc_module.get("briefSummary"),
                        "startDate": status_module.get("startDateStruct", {}).get("date"),
                        "completionDate": status_module.get("completionDateStruct", {}).get("date")
                    })
                
                return {"results": results, "total": len(results)}
            else:
                return {"error": f"Clinical trials search failed: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

# AIDEV-SECTION: Variant Search Tool

async def search_variants(gene: str, variant_type: str = None, 
                         clinical_significance: str = None, limit: int = 20) -> Dict[str, Any]:
    """
    Search for genetic variants using MyVariant.info.
    
    Args:
        gene: Gene symbol (e.g., "BRCA1")
        variant_type: Type of variant (e.g., "SNP", "deletion")
        clinical_significance: Clinical significance (e.g., "pathogenic")
        limit: Maximum results
        
    Returns:
        Variant search results
    """
    # Build query
    query_parts = [f"gene:{gene}"]
    if variant_type:
        query_parts.append(f"variant_type:{variant_type}")
    if clinical_significance:
        query_parts.append(f"clinical_significance:{clinical_significance}")
    
    query = " AND ".join(query_parts)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{MYVARIANT_API}/query",
                params={
                    "q": query,
                    "size": limit,
                    "fields": "rsid,gene,variant,clinical,dbsnp,cadd,gnomad"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for hit in data.get("hits", []):
                    results.append({
                        "id": hit.get("_id"),
                        "rsid": hit.get("rsid"),
                        "gene": hit.get("gene", {}).get("symbol"),
                        "variant": hit.get("variant"),
                        "clinical": hit.get("clinical"),
                        "cadd": hit.get("cadd"),
                        "gnomad": hit.get("gnomad"),
                        "source": "MyVariant.info"
                    })
                
                return {"results": results, "total": data.get("total", len(results))}
            else:
                return {"error": f"Variant search failed: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}