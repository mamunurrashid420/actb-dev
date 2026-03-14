"""XBRL taxonomy assets - FASB US-GAAP concept labels and documentation.

This module provides two assets following medallion architecture:
- Bronze: Raw XML download from FASB
- Silver: Parsed parquet with concept → label mapping

The taxonomy provides human-readable labels for SEC XBRL concepts, which are
used to enrich the gold/sec/financials asset with friendly labels.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen

import dagster as dg
import pandas as pd

from pipelines.assets.sec.common import ASSET_GROUP

# FASB XBRL taxonomy URLs
# These are the official US-GAAP taxonomy files from FASB
FASB_BASE_URL = "https://xbrl.fasb.org/us-gaap/2024/elts"
LABEL_XML_URL = f"{FASB_BASE_URL}/us-gaap-lab-2024.xml"
DOC_XML_URL = f"{FASB_BASE_URL}/us-gaap-doc-2024.xml"

# XML namespaces used in FASB taxonomy files
NAMESPACES = {
    "link": "http://www.xbrl.org/2003/linkbase",
    "label": "http://www.xbrl.org/2003/linkbase",
    "xlink": "http://www.w3.org/1999/xlink",
}


def _download_xml(url: str) -> bytes:
    """Download XML file with proper headers."""
    headers = {
        "User-Agent": "actBI/1.0 (Data Pipeline; contact@actbi.ai)",
        "Accept": "application/xml",
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=120) as response:
        return response.read()


def _parse_label_xml(xml_bytes: bytes) -> dict[str, str]:
    """Parse label XML to extract concept → label mapping.

    Returns dict mapping concept names to their standard labels.
    """
    root = ET.fromstring(xml_bytes)
    labels: dict[str, str] = {}

    # Find all label elements
    # Format: <link:label xlink:label='lab_NetIncomeLoss' xlink:role='...role/label' ...>
    for label_elem in root.findall(".//link:label", NAMESPACES):
        label_role = label_elem.get(f"{{{NAMESPACES['xlink']}}}role", "")
        label_text = label_elem.text or ""

        # Only use standard labels (role ends with /label, not /terseLabel, /verboseLabel)
        if label_role == "http://www.xbrl.org/2003/role/label" and label_text:
            # Extract concept name from xlink:label attribute
            # Format: lab_ConceptName
            label_attr = label_elem.get(f"{{{NAMESPACES['xlink']}}}label", "")
            if label_attr and label_attr.startswith("lab_"):
                # Remove 'lab_' prefix to get concept name
                concept = label_attr[4:]  # Skip 'lab_'
                if concept and concept not in labels:
                    labels[concept] = label_text.strip()

    return labels


def _parse_doc_xml(xml_bytes: bytes) -> dict[str, str]:
    """Parse documentation XML to extract concept → documentation mapping.

    Returns dict mapping concept names to their documentation strings.
    """
    root = ET.fromstring(xml_bytes)
    docs: dict[str, str] = {}

    # Find all label elements (documentation is stored as labels with documentation role)
    # Format: <link:label xlink:label='lab_NetIncomeLoss' xlink:role='...role/documentation' ...>
    for label_elem in root.findall(".//link:label", NAMESPACES):
        label_role = label_elem.get(f"{{{NAMESPACES['xlink']}}}role", "")
        label_text = label_elem.text or ""

        # Documentation role
        if label_role == "http://www.xbrl.org/2003/role/documentation" and label_text:
            # Extract concept name from xlink:label attribute
            # Format: lab_ConceptName
            label_attr = label_elem.get(f"{{{NAMESPACES['xlink']}}}label", "")
            if label_attr and label_attr.startswith("lab_"):
                # Remove 'lab_' prefix to get concept name
                concept = label_attr[4:]  # Skip 'lab_'
                if concept and concept not in docs:
                    docs[concept] = label_text.strip()

    return docs


# =============================================================================
# BRONZE: Raw XML Download
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="xbrl_taxonomy_raw",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "fasb", "visibility": "internal"},
)
def bronze_xbrl_taxonomy_raw(
    context: dg.AssetExecutionContext,
) -> dict:
    """Download raw FASB XBRL taxonomy XML files.

    Downloads two files from FASB:
    - us-gaap-lab-2024.xml: Standard labels (~14MB)
    - us-gaap-doc-2024.xml: Documentation strings (~13MB)

    Stores raw XML in _data/assets/bronze/sec/xbrl_taxonomy_raw/
    """
    context.log.info("Downloading FASB US-GAAP taxonomy files...")

    output_dir = Path("_data/assets/bronze/sec/xbrl_taxonomy_raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download label XML
    context.log.info(f"Downloading labels from {LABEL_XML_URL}...")
    label_bytes = _download_xml(LABEL_XML_URL)
    label_path = output_dir / "us-gaap-lab-2024.xml"
    label_path.write_bytes(label_bytes)
    context.log.info(f"Downloaded labels: {len(label_bytes):,} bytes")

    # Download documentation XML
    context.log.info(f"Downloading documentation from {DOC_XML_URL}...")
    doc_bytes = _download_xml(DOC_XML_URL)
    doc_path = output_dir / "us-gaap-doc-2024.xml"
    doc_path.write_bytes(doc_bytes)
    context.log.info(f"Downloaded documentation: {len(doc_bytes):,} bytes")

    context.add_output_metadata({
        "label_xml_size": len(label_bytes),
        "doc_xml_size": len(doc_bytes),
        "label_path": str(label_path),
        "doc_path": str(doc_path),
    })

    return {
        "label_path": str(label_path),
        "doc_path": str(doc_path),
        "label_size": len(label_bytes),
        "doc_size": len(doc_bytes),
    }


# =============================================================================
# SILVER: Parsed Parquet
# =============================================================================


@dg.asset(
    key_prefix=["silver", "sec"],
    name="xbrl_taxonomy",
    group_name=ASSET_GROUP,
    metadata={"layer": "silver", "source": "fasb", "visibility": "internal"},
    ins={
        "xbrl_taxonomy_raw": dg.AssetIn(key=["bronze", "sec", "xbrl_taxonomy_raw"]),
    },
)
def silver_xbrl_taxonomy(
    context: dg.AssetExecutionContext,
    xbrl_taxonomy_raw: dict,
) -> pd.DataFrame:
    """Parse XBRL taxonomy XML to structured parquet.

    Parses the raw XML files to extract:
    - concept: XBRL concept name (e.g., "NetIncomeLoss")
    - label: Human-readable label (e.g., "Net Income (Loss)")
    - documentation: Full documentation string

    Returns DataFrame with ~18,000 US-GAAP concepts.
    """
    label_path = Path(xbrl_taxonomy_raw["label_path"])
    doc_path = Path(xbrl_taxonomy_raw["doc_path"])

    context.log.info("Parsing label XML...")
    label_bytes = label_path.read_bytes()
    labels = _parse_label_xml(label_bytes)
    context.log.info(f"Parsed {len(labels):,} concept labels")

    context.log.info("Parsing documentation XML...")
    doc_bytes = doc_path.read_bytes()
    docs = _parse_doc_xml(doc_bytes)
    context.log.info(f"Parsed {len(docs):,} concept documentation strings")

    # Combine labels and documentation into DataFrame
    # Use all concepts that have either a label or documentation
    all_concepts = set(labels.keys()) | set(docs.keys())
    context.log.info(f"Total unique concepts: {len(all_concepts):,}")

    records = []
    for concept in sorted(all_concepts):
        records.append({
            "concept": concept,
            "label": labels.get(concept, concept),  # Fallback to concept name
            "documentation": docs.get(concept, ""),
        })

    df = pd.DataFrame(records)

    # Stats for metadata
    has_label = (df["label"] != df["concept"]).sum()
    has_doc = (df["documentation"] != "").sum()

    context.add_output_metadata({
        "num_concepts": len(df),
        "num_with_label": int(has_label),
        "num_with_documentation": int(has_doc),
    })

    return df


__all__ = [
    "bronze_xbrl_taxonomy_raw",
    "silver_xbrl_taxonomy",
]
