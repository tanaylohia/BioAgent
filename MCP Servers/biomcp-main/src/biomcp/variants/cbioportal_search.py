"""cBioPortal search enhancements for variant queries."""

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ..utils.gene_validator import is_valid_gene_symbol, sanitize_gene_symbol
from ..utils.rate_limiter import cbioportal_limiter
from ..utils.request_cache import request_cache
from .cancer_types import get_cancer_keywords
from .external import CBIO_BASE_URL, CBIO_TOKEN

logger = logging.getLogger(__name__)

# Cache for frequently accessed data
_cancer_type_cache: dict[str, dict[str, Any]] = {}
_gene_panel_cache: dict[str, list[str]] = {}


class GeneHotspot(BaseModel):
    """Hotspot mutation information."""

    position: int
    amino_acid_change: str
    count: int
    frequency: float
    cancer_types: list[str] = Field(default_factory=list)


class CBioPortalSearchSummary(BaseModel):
    """Summary data from cBioPortal for a gene search."""

    gene: str
    total_mutations: int = 0
    total_samples_tested: int = 0
    mutation_frequency: float = 0.0
    hotspots: list[GeneHotspot] = Field(default_factory=list)
    cancer_distribution: dict[str, int] = Field(default_factory=dict)
    study_coverage: dict[str, Any] = Field(default_factory=dict)
    top_studies: list[str] = Field(default_factory=list)


class CBioPortalSearchClient:
    """Client for cBioPortal search operations."""

    def __init__(self):
        self.base_url = CBIO_BASE_URL
        self.headers = {}
        if CBIO_TOKEN:
            if not CBIO_TOKEN.startswith("Bearer "):
                self.headers["Authorization"] = f"Bearer {CBIO_TOKEN}"
            else:
                self.headers["Authorization"] = CBIO_TOKEN

    @request_cache(ttl=900)  # Cache for 15 minutes
    async def get_gene_search_summary(
        self, gene: str, max_studies: int = 10
    ) -> CBioPortalSearchSummary | None:
        """Get summary statistics for a gene across cBioPortal.

        Args:
            gene: Gene symbol (e.g., "BRAF")
            max_studies: Maximum number of studies to query

        Returns:
            Summary statistics or None if gene not found
        """
        # Validate and sanitize gene symbol
        if not is_valid_gene_symbol(gene):
            logger.warning(f"Invalid gene symbol: {gene}")
            return None

        gene = sanitize_gene_symbol(gene)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Apply rate limiting
                await cbioportal_limiter.wait_if_needed("cbioportal")

                # Get gene info first
                gene_resp = await client.get(
                    f"{self.base_url}/genes/{gene}", headers=self.headers
                )
                if gene_resp.status_code != 200:
                    logger.warning(f"Gene {gene} not found in cBioPortal")
                    return None

                gene_data = gene_resp.json()
                gene_id = gene_data.get("entrezGeneId")

                if not gene_id:
                    return None

                # Get cancer type keywords for this gene
                cancer_keywords = get_cancer_keywords(gene)

                # Get relevant molecular profiles in parallel with cancer types
                profiles_task = self._get_relevant_profiles(
                    client, gene, cancer_keywords
                )
                cancer_types_task = self._get_cancer_types(client)

                profiles, cancer_types = await asyncio.gather(
                    profiles_task, cancer_types_task
                )

                if not profiles:
                    logger.info(f"No relevant profiles found for {gene}")
                    return None

                # Query mutations from top studies
                selected_profiles = profiles[:max_studies]
                mutation_summary = await self._get_mutation_summary(
                    client, gene_id, selected_profiles, cancer_types
                )

                # Build summary
                summary = CBioPortalSearchSummary(
                    gene=gene,
                    total_mutations=mutation_summary.get("total_mutations", 0),
                    total_samples_tested=mutation_summary.get(
                        "total_samples", 0
                    ),
                    mutation_frequency=mutation_summary.get("frequency", 0.0),
                    hotspots=mutation_summary.get("hotspots", []),
                    cancer_distribution=mutation_summary.get(
                        "cancer_distribution", {}
                    ),
                    study_coverage={
                        "total_studies": len(profiles),
                        "queried_studies": len(selected_profiles),
                        "studies_with_data": mutation_summary.get(
                            "studies_with_data", 0
                        ),
                    },
                    top_studies=[
                        p.get("studyId", "")
                        for p in selected_profiles
                        if p.get("studyId")
                    ][:5],
                )

                return summary

        except httpx.TimeoutException:
            logger.error(
                f"cBioPortal API timeout for gene {gene}. "
                "The API may be slow or unavailable. Try again later."
            )
            return None
        except httpx.NetworkError as e:
            logger.error(
                f"Network error accessing cBioPortal for gene {gene}: {e}. "
                "Check your internet connection."
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error getting cBioPortal summary for {gene}: "
                f"{type(e).__name__}: {e}. "
                "This may be a temporary issue. If it persists, please report it."
            )
            return None

    async def _get_cancer_types(
        self, client: httpx.AsyncClient
    ) -> dict[str, dict[str, Any]]:
        """Get cancer type hierarchy (cached)."""
        if _cancer_type_cache:
            return _cancer_type_cache

        try:
            resp = await client.get(
                f"{self.base_url}/cancer-types", headers=self.headers
            )
            if resp.status_code == 200:
                cancer_types = resp.json()
                # Build lookup by ID
                for ct in cancer_types:
                    ct_id = ct.get("cancerTypeId")
                    if ct_id:
                        _cancer_type_cache[ct_id] = ct
                return _cancer_type_cache
        except Exception as e:
            logger.warning(f"Failed to get cancer types: {e}")

        return {}

    async def _get_relevant_profiles(
        self,
        client: httpx.AsyncClient,
        gene: str,
        cancer_keywords: list[str],
    ) -> list[dict[str, Any]]:
        """Get molecular profiles relevant to the gene."""
        try:
            # Get all mutation profiles
            await cbioportal_limiter.wait_if_needed("cbioportal")
            resp = await client.get(
                f"{self.base_url}/molecular-profiles",
                params={"molecularAlterationType": "MUTATION_EXTENDED"},
                headers=self.headers,
            )

            if resp.status_code != 200:
                return []

            all_profiles = resp.json()

            # Filter by cancer keywords
            relevant_profiles = []
            for profile in all_profiles:
                study_id = profile.get("studyId", "").lower()
                if any(keyword in study_id for keyword in cancer_keywords):
                    relevant_profiles.append(profile)

            # Sort by sample count (larger studies first)
            # Note: We'd need to fetch study details for actual sample counts
            # For now, prioritize known large studies
            priority_studies = [
                "msk_impact",
                "tcga",
                "genie",
                "metabric",
                "broad",
            ]

            def study_priority(profile):
                study_id = profile.get("studyId", "").lower()
                for i, priority in enumerate(priority_studies):
                    if priority in study_id:
                        return i
                return len(priority_studies)

            relevant_profiles.sort(key=study_priority)

            return relevant_profiles

        except Exception as e:
            logger.warning(f"Failed to get profiles: {e}")
            return []

    async def _get_mutation_summary(
        self,
        client: httpx.AsyncClient,
        gene_id: int,
        profiles: list[dict[str, Any]],
        cancer_types: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Get mutation summary across selected profiles."""
        # Query mutations from each profile
        mutation_tasks = []
        for profile in profiles:
            profile_id = profile.get("molecularProfileId")
            study_id = profile.get("studyId")
            if profile_id and study_id:
                task = self._get_profile_mutations(
                    client, gene_id, profile_id, study_id
                )
                mutation_tasks.append((task, study_id))

        # Execute in parallel
        results = await asyncio.gather(
            *[t[0] for t in mutation_tasks], return_exceptions=True
        )

        # Process results using helper function
        from .cbioportal_search_helpers import (
            format_hotspots,
            process_mutation_results,
        )

        mutation_data = await process_mutation_results(
            list(zip(results, [t[1] for t in mutation_tasks], strict=False)),
            cancer_types,
            self,
            client,
        )

        # Calculate frequency
        frequency = (
            mutation_data["total_mutations"] / mutation_data["total_samples"]
            if mutation_data["total_samples"] > 0
            else 0.0
        )

        # Format hotspots
        hotspots = format_hotspots(
            mutation_data["hotspot_counts"], mutation_data["total_mutations"]
        )

        return {
            "total_mutations": mutation_data["total_mutations"],
            "total_samples": mutation_data["total_samples"],
            "frequency": frequency,
            "hotspots": hotspots,
            "cancer_distribution": mutation_data["cancer_distribution"],
            "studies_with_data": mutation_data["studies_with_data"],
        }

    async def _get_profile_mutations(
        self,
        client: httpx.AsyncClient,
        gene_id: int,
        profile_id: str,
        study_id: str,
    ) -> dict[str, Any] | None:
        """Get mutations for a gene in a specific profile."""
        try:
            # Get sample count for the study
            samples_resp = await client.get(
                f"{self.base_url}/studies/{study_id}/samples",
                params={"projection": "SUMMARY"},
                headers=self.headers,
            )

            sample_count = (
                len(samples_resp.json())
                if samples_resp.status_code == 200
                else 0
            )

            # Get mutations
            mut_resp = await client.get(
                f"{self.base_url}/molecular-profiles/{profile_id}/mutations",
                params={
                    "sampleListId": f"{study_id}_all",
                    "geneIdType": "ENTREZ_GENE_ID",
                    "geneIds": str(gene_id),
                    "projection": "SUMMARY",
                },
                headers=self.headers,
            )

            if mut_resp.status_code == 200:
                mutations = mut_resp.json()
                return {"mutations": mutations, "sample_count": sample_count}

        except Exception as e:
            logger.debug(
                f"Failed to get mutations for {profile_id}: {type(e).__name__}"
            )

        return None

    async def _get_study_cancer_type(
        self,
        client: httpx.AsyncClient,
        study_id: str,
        cancer_types: dict[str, dict[str, Any]],
    ) -> str:
        """Get cancer type name for a study."""
        try:
            resp = await client.get(
                f"{self.base_url}/studies/{study_id}", headers=self.headers
            )
            if resp.status_code == 200:
                study = resp.json()
                cancer_type_id = study.get("cancerTypeId")
                if cancer_type_id and cancer_type_id in cancer_types:
                    return cancer_types[cancer_type_id].get("name", "Unknown")
                elif cancer_type := study.get("cancerType"):
                    return cancer_type.get("name", "Unknown")
        except Exception:
            logger.debug(f"Failed to get cancer type for study {study_id}")

        # Fallback: infer from study ID
        study_lower = study_id.lower()
        if "brca" in study_lower or "breast" in study_lower:
            return "Breast Cancer"
        elif "lung" in study_lower or "nsclc" in study_lower:
            return "Lung Cancer"
        elif "coad" in study_lower or "colorectal" in study_lower:
            return "Colorectal Cancer"
        elif "skcm" in study_lower or "melanoma" in study_lower:
            return "Melanoma"
        elif "prad" in study_lower or "prostate" in study_lower:
            return "Prostate Cancer"

        return "Unknown"


def format_cbioportal_search_summary(
    summary: CBioPortalSearchSummary | None,
) -> str:
    """Format cBioPortal search summary for display."""
    if not summary:
        return ""

    lines = [
        f"\n### cBioPortal Summary for {summary.gene}",
        f"- **Mutation Frequency**: {summary.mutation_frequency:.1%} ({summary.total_mutations:,} mutations in {summary.total_samples_tested:,} samples)",
        f"- **Studies**: {summary.study_coverage.get('studies_with_data', 0)} of {summary.study_coverage.get('queried_studies', 0)} studies have mutations",
    ]

    if summary.hotspots:
        lines.append("\n**Top Hotspots:**")
        for hs in summary.hotspots[:3]:
            lines.append(
                f"- {hs.amino_acid_change}: {hs.count} cases ({hs.frequency:.1%}) in {', '.join(hs.cancer_types[:3])}"
            )

    if summary.cancer_distribution:
        lines.append("\n**Cancer Type Distribution:**")
        for cancer_type, count in sorted(
            summary.cancer_distribution.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]:
            lines.append(f"- {cancer_type}: {count} mutations")

    return "\n".join(lines)
