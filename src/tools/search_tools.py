# AIDEV-SECTION: Direct Implementation of All Search Tools
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import json

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
    academic_params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,  # Clean query - let CSE handle the filtering
        "num": min(limit, 10),  # Google limits to 10 results per request
        "lr": "lang_en",  # Language restriction to English
        "fileType": "pdf",  # Prefer PDF documents
        "exactTerms": "research OR study OR clinical OR trial OR analysis OR review",  # Academic terms
        "orTerms": "pubmed nature science cell lancet nejm jama bmj plos arxiv biorxiv medrxiv"  # Key sources
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
                    params={"query": query, "limit": limit}
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

# AIDEV-SECTION: PubMed and Preprint Tools

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
                    results.append({
                        "pmid": article.get("pmid"),
                        "title": article.get("title"),
                        "authors": article.get("authorString"),
                        "abstract": article.get("abstractText"),
                        "journal": article.get("journalTitle"),
                        "year": article.get("pubYear"),
                        "doi": article.get("doi"),
                        "source": "PubMed"
                    })
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
                            results[server].append({
                                "title": article.get("title"),
                                "authors": article.get("authors"),
                                "abstract": article.get("abstract"),
                                "doi": article.get("doi"),
                                "date": article.get("date"),
                                "category": article.get("category"),
                                "source": server
                            })
                            
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