# Bio Agent - Comprehensive Project Requirements Document (PRD)

## Executive Summary

Based on the analysis of 7 MCP bio servers and existing plan.md architecture, we're building a **modular, FastAPI-based deep search bio agent** that orchestrates 60-70+ biological tools through MCP integration. The system will transform user queries into validated gene-level insights using traceable reasoning, low latency, and hot-pluggable extensibility.

## 1. Project Vision & Goals

### Primary Goal
Deliver a unified biomedical research assistant that combines:
- **Web Research Agent**: Structured literature and data mining  
- **MCP Tool Orchestra**: 60+ specialized biological tools
- **Intelligent Reasoning**: Multi-step hypothesis generation and validation
- **Traceable Insights**: Full provenance from query to conclusion

### Success Criteria
- Response time < 5s for simple queries, < 30s for complex workflows (However, we will keep it flexible initially)
- 90%+ workflow completion rate with full traceability
- Natural language interface for complex bioinformatics operations
- Hot-pluggable tool integration without system downtime

## 2. MCP Server Integration Strategy

### Tier 1: Essential (Immediate Implementation)
**BioMCP** (13 tools) - Core biomedical hub
- Literature: PubMed/PubTator3, bioRxiv/medRxiv
- Clinical: ClinicalTrials.gov
- Genomics: MyVariant.info, cBioPortal, TCGA 
- **Integration Priority**: HIGHEST

**Academic Search Integration** - Literature search (MOVED TO SEARCH AGENT)
- Semantic Scholar, CrossRef integration  
- Paper metadata and abstracts
- **Integration**: Core functionality of the Web Search Agent
- **Deep Research Toggle**: Extended research with thinking framework when enabled

**UniProt MCP** (26 tools) - Protein analysis
- Comprehensive protein database access
- Structural/functional analysis, comparative genomics
- **Integration Priority**: HIGHEST
**BioOntology MCP** (10 tools) - Terminology standardization
- 1,200+ biological ontologies via BioPortal
- Text annotation and semantic enrichment
- **Integration Priority**: HIGHEST

**Ensembl MCP** (25 tools) - Genomic analysis
- Gene-centric analysis, cross-species comparison
- Variants, regulatory elements, sequences
- **Integration Priority**: HIGHEST

### Tier 2: High Value (Secondary Implementation)
**Reactome MCP** (8 tools) - Pathway analysis
- Curated biological pathways
- Disease-pathway associations
- **Integration Priority**: HIGH

### Tier 3: Consider Enhancement
**Gene Ontology MCP** (4 tools) - Basic GO operations
- Limited functionality, potential for enhancement
- **Integration Priority**: MODERATE

**Total Available Tools**: 89 tools across 7 servers

## 3. System Architecture (Following plan.md)

### Simplified Micro-Service Architecture
```
Bio Agent System
├── orchestrator_service (FastAPI Orchestrator)
├── search_agent_service (Academic search + Deep research toggle)
│   ├── regular_search (Quick academic paper search)
│   └── deep_research (Extended thinking framework)
├── tools_agent_service (Categorized MCP tools with toggles)
│   ├── protein_tools (UniProt MCP)
│   ├── genomics_tools (Ensembl MCP) 
│   ├── literature_tools (BioMCP literature)
│   ├── clinical_tools (BioMCP clinical trials)
│   ├── ontology_tools (BioOntology MCP)
│   ├── pathway_tools (Reactome MCP)
│   └── variant_tools (BioMCP variants)
├── tool_planning_service (Determines which tool categories to use)
├── analysis_service (Integrates evidence → AnalysisReport)
└── response_composer_service (Formats user output)
```

### Technology Stack (per plan.md)
- **FastAPI**: HTTP micro-services
- **Pydantic v2**: Strict schema enforcement
- **OpenAI Agents SDK + MCP**: Tool integration runtime
- **Redis Streams**: Event-bus backbone
- **SQLAlchemy + Postgres**: Metadata persistence
- **S3/GCS**: Object store for artifacts
- **Sentence-Transformers**: Tool & doc embeddings
- **Docker + Kubernetes**: Packaging & autoscale

### Technology Stack Evaluation & Recommendations

#### Current Stack Analysis
**✅ RECOMMENDED - Keep Current:**

**FastAPI** - HTTP micro-services
- **Benefits**: Fast, modern, auto-documentation, async support
- **Trade-offs**: Python ecosystem (vs Node.js)  
- **Verdict**: ✅ Excellent choice for bio APIs

**Pydantic v2** - Schema enforcement  
- **Benefits**: Type safety, validation, performance improvements
- **Trade-offs**: Learning curve, Python-specific
- **Verdict**: ✅ Essential for data integrity

**Redis Streams** - Event-bus backbone
- **Benefits**: Built-in persistence, scaling, message durability
- **Trade-offs**: More complex than simple pub/sub
- **Verdict**: ✅ Good for workflow orchestration

**PostgreSQL** - Metadata persistence
- **Benefits**: ACID, JSON support, mature ecosystem
- **Trade-offs**: Heavier than NoSQL for simple data
- **Verdict**: ✅ Right choice for structured metadata

#### ⚠️ ALTERNATIVES TO CONSIDER:

**Docker + Kubernetes** → **Docker + Docker Compose** (Development)
- **Current**: Full K8s setup
- **Alternative**: Docker Compose for development, K8s for production
- **Benefits**: Simpler local development, faster iteration
- **Trade-offs**: Need separate production setup

**S3/GCS** → **MinIO** (Development) 
- **Current**: Cloud object storage
- **Alternative**: Local MinIO for development
- **Benefits**: Faster local development, no cloud costs
- **Trade-offs**: Different APIs, separate production config

#### 🔄 RECOMMENDATIONS FOR EVALUATION:

**OpenAI Agents SDK** → **LangChain + Custom MCP Client**
- **Benefits**: More control, framework flexibility, cost optimization
- **Trade-offs**: More implementation work, less integrated
- **Recommendation**: Start with OpenAI Agents, evaluate after M4

**Sentence-Transformers** → **OpenAI Embeddings**
- **Benefits**: Cloud-based, consistent, no model management  
- **Trade-offs**: API costs, external dependency
- **Recommendation**: Cost analysis after initial implementation

#### 💡 ADDITIONAL CONSIDERATIONS:

**Caching Layer**: Add **Redis** for aggressive caching of MCP tool results
**Monitoring**: **Sentry** for error tracking alongside Prometheus
**Message Queue**: Consider **Celery** for long-running background tasks

## 4. Data & Artifact Schemas

### Core Pydantic Models (from plan.md)
| Model | Key Fields | Purpose |
|-------|------------|---------|
| `TaskSpec` | id, user_query, constraints | Initial request specification |
| `ResearchPlan` | goals[], query_templates[], depth_params | Research strategy |
| `ResearchDump` | doc_manifest_url, embedding_store_ref | Literature corpus |
| `HypothesisSet` | hypotheses[], evidence_refs[], confidence | Generated hypotheses |
| `ValidationPlan` | hypothesis_id, tool_sequence[], bindings | Tool execution plan |
| `ToolResultBundle` | call_id, status, payload, provenance | Tool execution results |
| `AnalysisReport` | findings[], next_steps, confidence_matrix | Final insights |

## 5. Updated Control Flow (Toggle-Based Architecture)

### User Interface Flow
**Frontend Search Interface** with configurable toggles:
- **Search Query Input**: Natural language research question
- **Deep Research Toggle**: ON/OFF for extended thinking framework  
- **Tool Category Toggles**: Enable specific tool categories as needed
  - 🧬 Protein Research (UniProt tools)
  - 🧬 Genomics Analysis (Ensembl tools) 
  - 📚 Literature Search (BioMCP literature tools)
  - 🏥 Clinical Trials (BioMCP clinical tools)
  - 📖 Ontology/Terms (BioOntology tools)
  - 🔬 Pathways (Reactome tools)
  - 🧪 Variants (BioMCP variant tools)

### Simplified 5-Step Workflow

1. **POST /search** → Orchestrator ↳ Validates toggles & routes request
   - **Frontend Receives**: `task_id`, `enabled_modes`, `estimated_duration`

2. **Search Agent** executes based on toggles
   - **Regular Search**: Quick academic paper retrieval
   - **Deep Research** (if toggled): Extended thinking framework with research planning
   - **Frontend Receives**: `search_results[]`, `research_plan` (if deep mode), `progress: 40%`

3. **Tool Planning Service** determines which tools to execute (based on enabled toggles)
   - Maps user query + search results to relevant tool categories
   - **Frontend Receives**: `selected_tools[]`, `tool_categories_active[]`, `progress: 60%`

4. **Tools Agent** executes enabled tool categories in parallel
   - Each category handled by specialized sub-agent
   - **Frontend Receives**: `tool_results[]`, `category_status[]`, `progress: 80%`

5. **Analysis & Response** integrates all results  
   - **Frontend Receives**: `final_report`, `citations[]`, `tool_insights[]`, `progress: 100%`

### Tool Categories & MCP Server Mapping

| Category | MCP Server(s) | Tools Count | Sub-Agent |
|----------|---------------|-------------|-----------|
| 🧬 **Protein Research** | UniProt MCP | 26 tools | protein_agent |
| 🧬 **Genomics Analysis** | Ensembl MCP | 25 tools | genomics_agent |  
| 📚 **Literature Search** | BioMCP + Academic Search | 6 tools | literature_agent |
| 🏥 **Clinical Trials** | BioMCP | 5 tools | clinical_agent |
| 📖 **Ontology/Terms** | BioOntology MCP | 10 tools | ontology_agent |
| 🔬 **Pathways** | Reactome MCP | 8 tools | pathway_agent |
| 🧪 **Variants** | BioMCP | 2 tools | variant_agent |

**Total**: 82 tools across 7 specialized sub-agents

## 6. Repository Structure & Organization

### High-Level Directory Structure
```
Bio_Agent_BackEnd/
├── src/
│   ├── orchestrator/           # Main orchestrator service
│   ├── search_agent/          # Search agent with deep research toggle
│   │   ├── regular_search/    # Quick academic search
│   │   └── deep_research/     # Extended thinking framework
│   ├── tools_agent/           # Categorized tool agents  
│   │   ├── protein_agent/     # UniProt MCP integration
│   │   ├── genomics_agent/    # Ensembl MCP integration
│   │   ├── literature_agent/  # BioMCP literature tools
│   │   ├── clinical_agent/    # BioMCP clinical trials
│   │   ├── ontology_agent/    # BioOntology MCP integration
│   │   ├── pathway_agent/     # Reactome MCP integration
│   │   └── variant_agent/     # BioMCP variant tools
│   ├── tool_planning/         # Tool selection and routing
│   ├── analysis/              # Evidence integration & synthesis
│   ├── response_composer/     # Output formatting
│   └── shared/               # Common utilities, schemas, configs
├── mcp_servers/              # Local MCP server instances
│   ├── biomcp/              # BioMCP server
│   ├── academic_search/     # Academic Search server
│   ├── uniprot/            # UniProt server  
│   ├── bioontology/        # BioOntology server
│   ├── ensembl/           # Ensembl server
│   ├── reactome/          # Reactome server
│   └── gene_ontology/     # Gene Ontology server
├── frontend_api/          # FastAPI endpoints for frontend
├── config/               # Configuration files
├── tests/               # Test suites
├── docs/               # Documentation
└── deployment/        # Docker, K8s, CI/CD configs
```

### Toggle-Based Feature Architecture
- **Search Toggles**: Regular vs Deep Research mode selection
- **Tool Category Toggles**: Independent enable/disable for each tool category  
- **Progressive Enhancement**: Start with basic search, add tool categories incrementally
- **Modular Integration**: Each MCP server can be integrated independently

## 7. MCP Tool Integration Details

### Tool Registry Integration
- **Startup**: Scan `tools/*.plugin.json`, register with `ToolRegistry.register_from_mcp()`
- **Planning**: `registry.nearest_tools(query,k)` for context optimization
- **Execution**: `registry.execute_tools(batch, parallel=True)` with caching
- **Hot Reload**: `POST /reload_tools` triggers refresh without downtime

### API Requirements by Server
| Server | API Key | Rate Limits | Dependencies |
|--------|---------|-------------|--------------|
| BioMCP | Optional (CBIO_TOKEN) | Varies by service | uv, biomcp-python |
| Academic Search | Optional | Standard | httpx, mcp |  
| UniProt | None | Standard | axios, node.js |
| BioOntology | Required (BioPortal) | 60s timeout | axios, node.js |
| Ensembl | None | 15 req/sec | axios, node.js |
| Reactome | None | 30s timeout | axios, node.js |
| Gene Ontology | None | 30s timeout | axios, node.js |

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
**M0**: Repo skeleton, Pydantic models, CI checks
**M1**: Orchestrator + Redis Streams + `POST /task` stub  
**M2**: MVP Planner → generates 5 search queries
**M3**: ResearchDump service fetches docs into S3

### Phase 2: Core Integration (Weeks 5-8) 
**M4**: ToolRegistry boot with Tier 1 MCP tools (BioMCP, UniProt, Academic Search)
**M5**: Executor fan-out, cache, retry for initial 42 tools
**M6**: End-to-end slice validates one hypothesis
**M7**: BioOntology and Ensembl integration (+35 tools)

### Phase 3: Enhancement (Weeks 9-12)
**M8**: Reactome integration, full 89-tool orchestration
**M9**: Advanced workflow capabilities and optimization
**M10**: Performance tuning, scale testing
**M11**: Comprehensive testing suite

### Phase 4: Production (Weeks 13-16)  
**M12**: Observability, security hardening
**M13**: Documentation and deployment configs
**M14**: Performance monitoring, alerting
**M15**: Production readiness validation

## 9. Detailed Step-by-Step Task List

### Repository Setup & Architecture (Week 1)
1. Initialize FastAPI project structure with 8 microservices
2. Setup Pydantic v2 models for all 7 artifact schemas  
3. Configure Docker containerization for each service
4. Setup Redis Streams message bus configuration
5. Initialize SQLAlchemy + Postgres for metadata
6. Setup S3/GCS object store integration
7. Configure CI/CD pipeline with GitHub Actions
8. Setup development environment with docker-compose

### MCP Server Integration Layer (Weeks 2-4)
9. Implement ToolRegistry with OpenAI Agents MCP extension
10. Create MCP server connection managers for all 7 servers
11. Implement tool discovery and schema validation
12. Build caching layer for tool results with Redis
13. Create retry and error handling mechanisms
14. Implement tool execution batching and parallelization
15. Build hot-reload capability for tool updates
16. Setup tool embeddings with Sentence-Transformers

### Web Research Agent (Weeks 3-5)
17. Implement web_planner_service with deep thinking prompts
18. Build research_dump_service for document fetching
19. Integrate with BioMCP literature search (PubMed, bioRxiv) 
20. Implement Academic Search MCP integration
21. Build document normalization and chunking
22. Create embedding store for retrieved documents
23. Implement relevance scoring and ranking
24. Build corpus management and versioning

### Hypothesis Generation & Validation (Weeks 4-6)
25. Implement hypothesis_service for mining and clustering
26. Build confidence scoring algorithms
27. Create gene_validation_planner_service 
28. Implement hypothesis-to-tools mapping logic
29. Build validation plan generation
30. Create tool sequence optimization
31. Implement parameter binding and validation
32. Build validation result aggregation

### Tool Orchestration Engine (Weeks 5-8)
33. Implement tool_executor_service with async execution
34. Integrate all Tier 1 MCP servers (BioMCP, UniProt, Academic Search, BioOntology, Ensembl)
35. Build parallel execution with proper rate limiting
36. Implement result caching and deduplication  
37. Create execution monitoring and logging
38. Build failure recovery and partial result handling
39. Implement tool usage analytics and optimization
40. Create tool performance monitoring

### Analysis & Response Generation (Weeks 7-9)
41. Implement analysis_service for evidence integration
42. Build confidence matrix generation
43. Create finding synthesis algorithms
44. Implement next steps recommendation logic
45. Build response_composer_service for user output
46. Create multiple output format support
47. Implement citation and provenance tracking
48. Build interactive result exploration

### Observability & Security (Weeks 10-12)
49. Implement distributed tracing with OpenTelemetry
50. Setup Prometheus metrics collection
51. Build Grafana dashboards for system monitoring
52. Implement security with JWT authentication
53. Setup secrets management with Vault/AWS Secrets
54. Implement data classification and PII protection
55. Build audit logging and compliance tracking
56. Create performance alerting and SLA monitoring

### Testing & Quality Assurance (Weeks 11-15)
57. Create unit tests for all microservices
58. Build integration tests for MCP tool interactions
59. Implement end-to-end workflow testing
60. Create performance and load testing suite
61. Build data quality validation tests
62. Implement chaos engineering tests
63. Create regression testing automation
64. Build user acceptance testing framework

### Documentation & Deployment (Weeks 14-16)  
65. Create comprehensive API documentation
66. Build user guides and tutorials
67. Implement tool catalog and discovery interface
68. Create deployment guides for different environments
69. Build monitoring and troubleshooting guides
70. Create developer onboarding documentation
71. Implement automated deployment pipelines
72. Create production runbooks and procedures

## 10. Success Metrics & KPIs

### Performance Metrics
- Query Response Time: < 5s (95th percentile simple queries)
- Complex Workflow Time: < 30s (95th percentile)
- Tool Integration Uptime: > 99.5%
- System Availability: > 99.9%

### Quality Metrics  
- Workflow Success Rate: > 90%
- Tool Execution Success Rate: > 95%
- Result Accuracy: > 85% (validated against expert review)
- User Satisfaction: > 4.2/5.0

### Scale Metrics
- Concurrent Users: Support 100+ simultaneous queries  
- Tool Orchestration: Handle 89 tools with < 100ms latency overhead
- Data Throughput: Process 1M+ documents per hour
- Cost Efficiency: < $0.10 per complex query

## 11. Risk Assessment & Mitigation

### Technical Risks
- **MCP Server Dependencies**: Fallback mechanisms and redundancy
- **Rate Limiting**: Intelligent queuing and caching strategies
- **Data Quality**: Validation pipelines and confidence scoring
- **System Complexity**: Comprehensive monitoring and alerting

### Mitigation Strategies  
- Multi-source data redundancy for critical functions
- Aggressive caching with TTL management
- Circuit breaker patterns for external dependencies
- Graceful degradation with partial results

## 12. MCP Server Detailed Analysis

### BioMCP (13 Tools) - Priority: HIGHEST
**Capabilities:**
- Literature search (PubMed/PubTator3, bioRxiv/medRxiv)
- Clinical trials (ClinicalTrials.gov)  
- Genomic variants (MyVariant.info, cBioPortal, TCGA)
- Sequential thinking framework

**Tools:** think, search, fetch, article_searcher, article_getter, trial_searcher, trial_getter, trial_protocol_getter, trial_references_getter, trial_outcomes_getter, trial_locations_getter, variant_searcher, variant_getter

**Integration:** Core hub for biomedical research workflows

### UniProt MCP (26 Tools) - Priority: HIGHEST  
**Capabilities:**
- Comprehensive protein database access
- Structural/functional analysis
- Comparative genomics and evolution
- Batch processing capabilities

**Key Tools:** search_proteins, get_protein_info, search_by_gene, get_protein_sequence, get_protein_features, compare_proteins, get_protein_homologs, get_protein_orthologs, get_phylogenetic_info, get_protein_structure, get_protein_domains_detailed, get_protein_variants, analyze_sequence_composition, get_protein_pathways, get_protein_interactions, batch_protein_lookup, advanced_search

**Integration:** Essential for protein research and analysis workflows

### Academic Search MCP (3 Tools) - Priority: HIGH
**Capabilities:**
- Academic paper search across multiple sources
- Paper metadata and abstract retrieval  
- Topic-based search with date filtering

**Tools:** search_papers, fetch_paper_details, search_by_topic

**Integration:** Complementary literature search to BioMCP

### BioOntology MCP (10 Tools) - Priority: HIGHEST
**Capabilities:**
- Access to 1,200+ biological ontologies via BioPortal
- Text annotation and semantic enrichment
- Batch processing for multiple texts

**Tools:** search_terms, search_properties, search_ontologies, get_ontology_info, annotate_text, recommend_ontologies, batch_annotate, get_class_info, get_ontology_metrics, get_analytics_data

**Integration:** Critical for terminology standardization across all biological domains

### Ensembl MCP (25 Tools) - Priority: HIGHEST
**Capabilities:**
- Gene-centric analysis with cross-species comparison
- Genomic data, variants, regulatory elements
- Sequence data and coordinate mapping

**Key Tools:** lookup_gene, get_transcripts, search_genes, get_sequence, get_cds_sequence, translate_sequence, get_homologs, get_gene_tree, get_variants, get_variant_consequences, get_regulatory_features, get_motif_features, get_xrefs, map_coordinates, list_species, get_assembly_info, batch_gene_lookup, batch_sequence_fetch

**Integration:** Essential for genomic analysis and gene information

### Reactome MCP (8 Tools) - Priority: HIGH
**Capabilities:**
- Curated biological pathways
- Disease-pathway associations
- Systems biology and molecular interactions

**Tools:** search_pathways, get_pathway_details, get_pathway_hierarchy, find_pathways_by_gene, find_pathways_by_disease, get_pathway_participants, get_pathway_reactions, get_protein_interactions

**Integration:** Important for pathway analysis and systems biology research

### Gene Ontology MCP (4 Tools) - Priority: MODERATE
**Capabilities:**
- Basic GO term search and validation
- Limited functional annotation capabilities

**Tools:** search_go_terms, get_go_term, validate_go_id, get_ontology_stats

**Integration:** Basic GO operations, may need enhancement or replacement

---

**Document Version**: 1.0  
**Created**: 2025-07-21  
**Author**: Bio Agent Development Team  
**Next Review**: Upon completion of Phase 1 Foundation