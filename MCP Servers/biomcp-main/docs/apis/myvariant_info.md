# MyVariant.info API

This document details the MyVariant.info API, which BioMCP uses for fetching genetic variant annotations. Understanding the underlying API fields and query syntax can aid advanced users and developers working with BioMCP.

## Overview

MyVariant.info is a comprehensive API that provides variant annotation
information from multiple databases in a centralized location. This document
outlines how to interface with this API to search for and retrieve information
about genetic variants.

> **CLI Documentation**: For information on using these APIs through the BioMCP
> command line interface, see
> the [Variants CLI Documentation](../cli/variants.md).

## API Endpoints

### Query API

**Endpoint:** `https://myvariant.info/v1/query`

This endpoint allows searching for variants using various query parameters.

#### Key Query Parameters

| Parameter | Description                              | Example                                                        |
| --------- | ---------------------------------------- | -------------------------------------------------------------- |
| `q`       | Query string using field:value syntax    | `dbnsfp.genename:BRAF AND dbnsfp.hgvsp:p.V600E`                |
| `fields`  | Comma-separated list of fields to return | `_id,dbsnp.rsid,dbnsfp.genename,clinvar.clinical_significance` |
| `size`    | Number of hits to return                 | `10`                                                           |
| `from`    | Number of hits to skip                   | `0`                                                            |
| `sort`    | Sort by specified field                  | `cadd.phred:desc`                                              |

#### Example Requests

Full variant search:

```bash
curl -X GET "https://myvariant.info/v1/query?q=dbnsfp.genename%3ABRAF%20AND%20dbnsfp.hgvsp%3Ap.V600E"
```

Partial variant search (selected fields):

```bash
curl -X GET "https://myvariant.info/v1/query?q=dbnsfp.genename%3ABRAF%20AND%20dbnsfp.hgvsp%3Ap.V600E&fields=_id,dbsnp.rsid,dbnsfp.genename,clinvar.clinical_significance,cadd.phred,gnomad_exome.af.af,exac.af,mutdb"
```

### Variant Retrieval API

**Endpoint:** `https://myvariant.info/v1/variant/{variant_id}`

This endpoint retrieves detailed information about a specific variant using its
ID.

Example:

```bash
curl -X GET "https://myvariant.info/v1/variant/chr7:g.140453136A>T"
```

## Implementation Strategy

### Query Construction

Constructing effective queries requires understanding the field structure. The
most common query patterns include:

1. **Gene + Variant**: `dbnsfp.genename:BRAF AND dbnsfp.hgvsp:p.V600E`
2. **dbSNP ID**: `dbsnp.rsid:rs113488022`
3. **Chromosome Position**: `_id:chr7:g.140453136A>T`

Code example for query building:

```python
def build_variant_query(gene=None, protein_change=None, rsid=None):
    query_parts = []

    if gene:
        query_parts.append(f"dbnsfp.genename:{gene}")
    if protein_change:
        query_parts.append(f"dbnsfp.hgvsp:{protein_change}")
    if rsid:
        query_parts.append(f"dbsnp.rsid:{rsid}")

    return " AND ".join(query_parts)
```

### Response Parsing

The API returns data in JSON format. Example response structure for a variant:

```json
{
  "took": 5,
  "total": 1,
  "max_score": 26.326775,
  "hits": [
    {
      "_id": "chr7:g.140453136A>T",
      "_score": 26.326775,
      "cadd": {
        "_license": "http://bit.ly/2TIuab9",
        "phred": 32
      },
      "dbnsfp": {
        "_license": "http://bit.ly/2VLnQBz",
        "genename": ["BRAF", "BRAF", "BRAF", "BRAF"]
      },
      "dbsnp": {
        "_license": "http://bit.ly/2AqoLOc",
        "rsid": "rs113488022"
      },
      "exac": {
        "_license": "http://bit.ly/2H9c4hg",
        "af": 0.00001647
      },
      "gnomad_exome": {
        "_license": "http://bit.ly/2I1cl1I",
        "af": {
          "af": 0.00000397994
        }
      }
    }
  ]
}
```

## Data Fields

The API provides rich variant annotation data from multiple sources, including:

1. **Basic Information**:

   - `_id`: Variant ID in HGVS format (e.g., `chr7:g.140453136A>T`)
   - `dbsnp.rsid`: dbSNP RS identifier (e.g., `rs113488022`)

2. **Functional Impact Scores**:

   - `cadd.phred`: CADD Phred score for variant deleteriousness
   - `mutpred_score`: MutPred score for amino acid substitutions

3. **Population Frequency**:

   - `gnomad_exome.af.af`: Frequency in gnomAD exome dataset
   - `exac.af`: Frequency in ExAC dataset

4. **Clinical Significance**:

   - `clinvar.clinical_significance`: Clinical significance from ClinVar

5. **Gene Information**:
   - `dbnsfp.genename`: Associated gene name(s)

## Authentication and Rate Limits

The MyVariant.info API is public and does not require authentication for basic
usage, but there are rate limits:

- **Anonymous Access**: Limited to 1,000 requests per IP per day
- **Registered Access**: Higher limits available with a free API key
- **Batch Queries**: Limited to 1,000 variants per request

## Best Practices

1. **Use Specific Queries**: Target exact genes, variants, or identifiers
2. **Limit Returned Fields**: Use the `fields` parameter to request only needed
   data
3. **Implement Caching**: Cache frequently accessed variant data
4. **Handle Errors Robustly**: Implement retry logic and proper error handling
5. **Batch Requests**: When possible, use batch endpoints for multiple variants

## Search Parameters

The following are the prioritized list of commonly used attributes for
searching MyVariant data:

### 1. Gene Symbol

- **Description**: Most common approach to find all known variants in a gene
- **Query Syntax**: `dbnsfp.genename:<GENE>`
- **Example**: `q=dbnsfp.genename:TP53`

### 2. cDNA Notation

- **Description**: Search by cDNA expression
- **Query Syntax**: `dbnsfp.hgvsc:<CDNA_EXPRESSION>`
- **Example**: `q=dbnsfp.hgvsc:c.1799T>A`

### 3. Protein (p.) Notation

- **Description**: Search by protein-level notation
- **Query Syntax**: `dbnsfp.hgvsp:<PROTEIN_EXPRESSION>`
- **Example**: `q=dbnsfp.hgvsp:p.V600E`

### 4. Genomic Region

- **Description**: Find all variants in a coordinate range
- **Query Syntax**: `chr<NUM>:<START>-<END>`
- **Example**: `q=chr7:140453100-140453200`
- **With Additional Filters**:
  `q=chr7:140453100-140453200 AND dbnsfp.genename:BRAF`

### 5. dbSNP rsID

- **Description**: Lookup by rsID
- **Query Syntax**: `dbsnp.rsid:<RSID>`
- **Example**: `q=dbsnp.rsid:rs113488022`

### 6. ClinVar Significance

- **Description**: Filter by clinical significance
- **Query Syntax**: `clinvar.clinical_significance:<VALUE>`
- **Example**: `q=clinvar.clinical_significance:Pathogenic`
- **Multiple Values**:
  `q=clinvar.clinical_significance:(Pathogenic OR Likely_pathogenic)`

### 7. Population Frequency

- **Description**: Filter by rarity or commonality
- **Query Syntax**: `gnomad_exome.af:<THRESHOLD>` or
  `exac.af:<OPERATOR><THRESHOLD>`
- **Example**: `q=gnomad_exome.af:<0.001` or `q=exac.af:>=0.01`

### 8. Functional Predictions

- **Description**: Filter by prediction scores
- **CADD**: `q=cadd.phred:>15`
- **PolyPhen**: `q=dbnsfp.polyphen2.hdiv.pred:probably_damaging` or
  `q=dbnsfp.polyphen2.hdiv.score:>0.9`
- **SIFT**: `q=dbnsfp.sift.pred:deleterious` or `q=dbnsfp.sift.score:<0.05`

### 9. COSMIC ID

- **Description**: Search by COSMIC mutation IDs
- **Query Syntax**: `cosmic.cosmic_id:<ID>` or `mutdb.cosmic_id:<ID>`
- **Example**: `q=cosmic.cosmic_id:476`

### 10. Combining Multiple Filters

- **Description**: Combine conditions for precise searches
- **Example**: `q=dbnsfp.genename:BRAF AND cadd.phred:>=20 AND exac.af:<0.001`

### Query Fields Reference Table

| Attribute               | MyVariant Field / Query Expression                                        |
| ----------------------- | ------------------------------------------------------------------------- |
| Gene Symbol             | `dbnsfp.genename:<GENE>`                                                  |
| cDNA Notation           | `dbnsfp.hgvsc:<NOTATION>`                                                 |
| Protein Notation        | `dbnsfp.hgvsp:<NOTATION>`                                                 |
| Genomic Region          | `chr7:140453100-140453200` (substitute correct chr, start, end)           |
| dbSNP rsID              | `dbsnp.rsid:<RSID>`                                                       |
| ClinVar Significance    | `clinvar.clinical_significance:<VALUE>`                                   |
| GnomAD / ExAC Frequency | `gnomad_exome.af:<FLOAT>` / `exac.af:>FLOAT`                              |
| CADD PHRED Score        | `cadd.phred:>FLOAT` (or `<, >=, <=`)                                      |
| PolyPhen2 Prediction    | `dbnsfp.polyphen2.hdiv.pred:(D OR P)` or `dbnsfp.polyphen2.hdiv.score:>X` |
| SIFT                    | `dbnsfp.sift.pred:deleterious` / `dbnsfp.sift.score:<0.05`                |
| COSMIC ID               | `cosmic.cosmic_id:<ID>` or `mutdb.cosmic_id:<ID>`                         |

## Data Integration

The Variants endpoint can be used to find variants based on their genomic
location (chr, start, ref, alt), converting to Gene and Protein change (HGVS)
and used to search Trials and Articles. This provides a powerful way to link
genetic information with clinical trials and literature.

## Output Format

For the API implementation, all data is typically returned in JSON format. BioMCP CLI commands render this data as Markdown by default (unless `--json` is specified).

When using the `biomcp variant search` command, a curated set of important fields (defined internally, plus those requested via `--sources`) is requested from the API to provide a concise summary.

When using the `biomcp variant get` command to retrieve a specific variant, BioMCP requests `fields=all` from the MyVariant.info API to get the most comprehensive data available for that variant, and then injects relevant database links.

## More Information

For complete API documentation, visit
the [MyVariant.info Documentation](https://docs.myvariant.info/).

### URLs

| Website/Database         | Identifier Used       | Data Field(s) in API Response                      | URL Construction Pattern                                                                 | Placement/Notes                                                                                                                                                                     |
| :----------------------- | :-------------------- | :------------------------------------------------- | :--------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| dbSNP                    | rsID                  | `dbsnp.rsid`                                       | `https://www.ncbi.nlm.nih.gov/snp/<rsID>`                                                | Standard link for SNP information. Include _if rsID exists_.                                                                                                                        |
| ClinVar (Variant)        | ClinVar Variation ID  | `clinvar.variation_id`                             | `https://www.ncbi.nlm.nih.gov/clinvar/variation/<VariationID>/`                          | Links to the variant page in ClinVar. Include _if Variation ID exists_.                                                                                                             |
| ClinVar (Interpretation) | ClinVar RCV Accession | `clinvar.rcv.accession`                            | `https://www.ncbi.nlm.nih.gov/clinvar/rcv/<RCV Accession>/`                              | Links to a specific interpretation record. Include _if RCV Accession exists_.                                                                                                       |
| COSMIC                   | COSMIC ID (Numeric)   | `cosmic.cosmic_id`                                 | `https://cancer.sanger.ac.uk/cosmic/mutation/overview?id=<COSMIC_ID_number>`             | Links to the mutation in COSMIC. Extract _only the number_ from the COSMIC ID (e.g., from `COSM12345`, use `12345`). Include _if COSMIC ID exists_.                                 |
| CIViC                    | CIViC Variant ID      | `civic.id` _or_ `civic.variant_id`                 | `https://civicdb.org/variants/<CIVIC_Variant_ID>/summary`                                | Links to the variant summary in CIViC. Include _if CIViC ID exists_.                                                                                                                |
| Ensembl                  | rsID _or_ Ensembl ID  | `dbsnp.rsid` _or_ `ensembl.variant.id`             | `https://ensembl.org/Homo_sapiens/Variation/Explore?v=<rsID>` (preferred if rsID exists) | Links to the variant in Ensembl. Prioritize using rsID if available.                                                                                                                |
| UCSC Genome Browser      | Genomic Coordinates   | `chrom`, `vcf.pos` (or `hg19.start`, `hg38.start`) | `https://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&position=<chr>:<start>-<end>`          | Links to the genomic region. Construct `start`/`end` around `vcf.pos`. Check genome build (hg38 is current, hg19 might be needed for older data). Requires chromosome and position. |
| HGNC (Gene Link)         | Gene Symbol           | `dbnsfp.genename`                                  | `https://www.genenames.org/data/gene-symbol-report/#!/symbol/<GeneSymbol>`               | Links to the associated gene's official nomenclature page. Useful context.                                                                                                          |
