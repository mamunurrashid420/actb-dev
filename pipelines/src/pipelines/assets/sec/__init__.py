"""SEC filing assets - medallion architecture.

This package contains SEC filing assets following medallion layers:

Bronze (raw downloads):
- bulk_downloads.py: company_facts_download, submissions
- taxonomy.py: xbrl_taxonomy_raw (FASB XML)
- fsds.py: fsds (Financial Statement Data Sets quarterly zip)
- form_13f.py: form_13f (API), form_13f_bulk (DERA bulk data sets)

Silver (parsed/structured):
- bulk_downloads.py: company_facts (parsed XBRL parquet)
- taxonomy.py: xbrl_taxonomy (concept → label mapping)
- registry.py: company_registry, institution_registry
- form_10k.py: form_10k_text, form_10k_sections, form_10k_financials
- form_10q.py: form_10q_text, form_10q_sections, form_10q_financials
- form_4.py: form_4, form_4_transactions
- form_13f.py: form_13f_holdings (merges API + bulk sources)
- fsds.py: fsds_segments, fsds_financials, fsds_company_metadata,
           fsds_subsidiaries, fsds_footnotes

Gold (LLM-visible):
- financials.py: SEC financials with semantic themes
- form_10k.py: annual_reports
- form_10q.py: quarterly_reports
- form_4.py: insider_activity
- form_13f.py: institutional_holdings
"""

# Export shared utilities
# Export bulk download assets
from pipelines.assets.sec.bulk_downloads import (
    bronze_company_facts_download,
    bronze_submissions,
    bronze_submissions_download,
    silver_company_facts,
)
from pipelines.assets.sec.common import (
    ASSET_GROUP,
    SecFilingConfig,
    extract_date_component,
    generate_financial_summary,
    generate_insider_summary,
    generate_portfolio_summary,
)

# Export gold financials asset (single unified asset with themes)
from pipelines.assets.sec.financials import gold_sec_financials

# Export Form 4 assets
from pipelines.assets.sec.form_4 import (
    bronze_form_4,
    gold_insider_activity,
    silver_form_4_transactions,
)

# Export Form 10-K assets
from pipelines.assets.sec.form_10k import (
    bronze_form_10k_text,
    gold_annual_reports,
    silver_form_10k_financials,
    silver_form_10k_sections,
)

# Export Form 10-Q assets
from pipelines.assets.sec.form_10q import (
    bronze_form_10q_text,
    gold_quarterly_reports,
    silver_form_10q_financials,
    silver_form_10q_sections,
)

# Export Form 13-F assets
from pipelines.assets.sec.form_13f import (
    bronze_form_13f,
    bronze_form_13f_bulk,
    gold_institutional_holdings,
    silver_form_13f_holdings,
)

# Export FSDS assets (Financial Statement Data Sets with segment data)
from pipelines.assets.sec.fsds import (
    bronze_fsds,
    gold_sec_company_profiles,
    gold_sec_segments,
    silver_fsds_company_metadata,
    silver_fsds_financials,
    silver_fsds_footnotes,
    silver_fsds_segments,
    silver_fsds_subsidiaries,
)

# Export registry assets
from pipelines.assets.sec.registry import (
    company_registry,
    institution_registry,
    sec_filer_registry,
)

# Export taxonomy assets
from pipelines.assets.sec.taxonomy import (
    bronze_xbrl_taxonomy_raw,
    silver_xbrl_taxonomy,
)

__all__ = [
    # Constants
    "ASSET_GROUP",
    # Runtime config
    "SecFilingConfig",
    # Helper functions
    "extract_date_component",
    "generate_financial_summary",
    "generate_insider_summary",
    "generate_portfolio_summary",
    # Registry assets
    "sec_filer_registry",
    "company_registry",
    "institution_registry",
    # Form 4 assets
    "bronze_form_4",
    "silver_form_4_transactions",
    "gold_insider_activity",
    # Form 10-K assets
    "bronze_form_10k_text",
    "silver_form_10k_sections",
    "silver_form_10k_financials",
    "gold_annual_reports",
    # Form 10-Q assets
    "bronze_form_10q_text",
    "silver_form_10q_sections",
    "silver_form_10q_financials",
    "gold_quarterly_reports",
    # Gold financials asset (single unified asset with themes)
    "gold_sec_financials",
    # Form 13-F assets
    "bronze_form_13f",
    "bronze_form_13f_bulk",
    "silver_form_13f_holdings",
    "gold_institutional_holdings",
    # Bulk download assets
    "bronze_company_facts_download",
    "bronze_submissions_download",
    "silver_company_facts",
    "bronze_submissions",
    # Taxonomy assets
    "bronze_xbrl_taxonomy_raw",
    "silver_xbrl_taxonomy",
    # FSDS assets (Financial Statement Data Sets with segment data)
    "bronze_fsds",
    "silver_fsds_segments",
    "silver_fsds_financials",
    "silver_fsds_company_metadata",
    "silver_fsds_subsidiaries",
    "silver_fsds_footnotes",
    "gold_sec_segments",
    "gold_sec_company_profiles",
]
