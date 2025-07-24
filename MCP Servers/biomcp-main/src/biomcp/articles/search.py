import json
from collections.abc import Generator
from typing import Annotated, Any, get_args

from pydantic import BaseModel, Field, computed_field

from .. import ensure_list, http_client, render
from ..constants import PUBTATOR3_SEARCH_URL, SYSTEM_PAGE_SIZE
from ..core import PublicationState
from .autocomplete import Concept, EntityRequest, autocomplete
from .fetch import call_pubtator_api

concepts: list[Concept] = sorted(get_args(Concept))
fields: list[str] = [concept + "s" for concept in concepts]


class PubmedRequest(BaseModel):
    chemicals: list[str] = Field(
        default_factory=list,
        description="List of chemicals for filtering results.",
    )
    diseases: list[str] = Field(
        default_factory=list,
        description="Diseases such as Hypertension, Lung Adenocarcinoma, etc.",
    )
    genes: list[str] = Field(
        default_factory=list,
        description="List of genes for filtering results.",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="List of other keywords for filtering results.",
    )
    variants: list[str] = Field(
        default_factory=list,
        description="List of variants for filtering results.",
    )

    def iter_concepts(self) -> Generator[tuple[Concept, str], None, None]:
        for concept in concepts:
            field = concept + "s"
            values = getattr(self, field, []) or []
            for value in values:
                yield concept, value


class PubtatorRequest(BaseModel):
    text: str
    size: int = 50


class ResultItem(BaseModel):
    pmid: int | None = None
    pmcid: str | None = None
    title: str | None = None
    journal: str | None = None
    authors: list[str] | None = None
    date: str | None = None
    doi: str | None = None
    abstract: str | None = None
    publication_state: PublicationState = PublicationState.PEER_REVIEWED
    source: str | None = Field(
        None, description="Source database (e.g., PubMed, bioRxiv, Europe PMC)"
    )

    @computed_field
    def pubmed_url(self) -> str | None:
        url = None
        if self.pmid:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"
        return url

    @computed_field
    def pmc_url(self) -> str | None:
        """Generates the PMC URL if PMCID exists."""
        url = None
        if self.pmcid:
            url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{self.pmcid}/"
        return url

    @computed_field
    def doi_url(self) -> str | None:
        """Generates the DOI URL if DOI exists."""
        url = None
        if self.doi:
            url = f"https://doi.org/{self.doi}"
        return url


class SearchResponse(BaseModel):
    results: list[ResultItem]
    page_size: int
    current: int
    count: int
    total_pages: int


async def convert_request(request: PubmedRequest) -> PubtatorRequest:
    query_parts = request.keywords[:]

    for concept, value in request.iter_concepts():
        entity = await autocomplete(
            request=EntityRequest(concept=concept, query=value),
        )
        if entity:
            query_parts.append(entity.entity_id)
        else:
            query_parts.append(value)

    query_text = " AND ".join(query_parts)

    return PubtatorRequest(text=query_text, size=SYSTEM_PAGE_SIZE)


async def add_abstracts(response: SearchResponse) -> None:
    pmids = [pr.pmid for pr in response.results if pr.pmid]
    abstract_response, _ = await call_pubtator_api(pmids, full=False)

    if abstract_response:
        for result in response.results:
            result.abstract = abstract_response.get_abstract(result.pmid)


def clean_authors(record):
    """Keep only the first and last author if > 4 authors."""
    authors = record.get("authors")
    if authors and len(authors) > 4:
        record["authors"] = [authors[0], "...", authors[-1]]
    return record


async def search_articles(
    request: PubmedRequest,
    output_json: bool = False,
) -> str:
    pubtator_request = await convert_request(request)

    response, error = await http_client.request_api(
        url=PUBTATOR3_SEARCH_URL,
        request=pubtator_request,
        response_model_type=SearchResponse,
        domain="article",
    )

    if response:
        await add_abstracts(response)
        # Add source field to PubMed results
        for result in response.results:
            result.source = "PubMed"

    # noinspection DuplicatedCode
    if error:
        data: list[dict[str, Any]] = [
            {"error": f"Error {error.code}: {error.message}"}
        ]
    else:
        data = list(
            map(
                clean_authors,
                [
                    result.model_dump(mode="json", exclude_none=True)
                    for result in (response.results if response else [])
                ],
            )
        )

    if data and not output_json:
        return render.to_markdown(data)
    else:
        return json.dumps(data, indent=2)


async def _article_searcher(
    call_benefit: Annotated[
        str,
        "Define and summarize why this function is being called and the intended benefit",
    ],
    chemicals: Annotated[
        list[str] | str | None, "List of chemicals for filtering results"
    ] = None,
    diseases: Annotated[
        list[str] | str | None,
        "Diseases such as Hypertension, Lung Adenocarcinoma, etc.",
    ] = None,
    genes: Annotated[
        list[str] | str | None, "List of genes for filtering results"
    ] = None,
    keywords: Annotated[
        list[str] | str | None, "List of other keywords for filtering results"
    ] = None,
    variants: Annotated[
        list[str] | str | None, "List of variants for filtering results"
    ] = None,
    include_preprints: Annotated[
        bool, "Include preprint articles from bioRxiv/medRxiv and Europe PMC"
    ] = True,
) -> str:
    """
    Searches for articles across PubMed and preprint servers.

    Parameters:
    - call_benefit: Define and summarize why this function is being called and the intended benefit
    - chemicals: List of chemicals for filtering results
    - diseases: Diseases such as Hypertension, Lung Adenocarcinoma, etc.
    - genes: List of genes for filtering results
    - keywords: List of other keywords for filtering results
    - variants: List of variants for filtering results
    - include_preprints: Include results from preprint servers (default: True)

    Notes:
    - Use full terms ("Non-small cell lung carcinoma") over abbreviations ("NSCLC")
    - Use keywords to specify terms that don't fit in disease, gene ("EGFR"),
      chemical ("Cisplatin"), or variant ("BRAF V600E") categories
    - Parameters can be provided as lists or comma-separated strings
    - Results include both peer-reviewed and preprint articles by default

    Returns:
    Markdown formatted list of matching articles, with peer-reviewed articles listed first.
    Limited to max 80 results (40 from each source).
    """
    # Import here to avoid circular dependency
    from .unified import search_articles_unified

    # Convert individual parameters to a PubmedRequest object
    request = PubmedRequest(
        chemicals=ensure_list(chemicals, split_strings=True),
        diseases=ensure_list(diseases, split_strings=True),
        genes=ensure_list(genes, split_strings=True),
        keywords=ensure_list(keywords, split_strings=True),
        variants=ensure_list(variants, split_strings=True),
    )

    return await search_articles_unified(
        request,
        include_pubmed=True,
        include_preprints=include_preprints,
    )
