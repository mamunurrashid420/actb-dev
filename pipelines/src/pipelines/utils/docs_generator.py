"""Documentation generator for Dagster assets.

Extracts metadata from Dagster asset definitions and generates
markdown documentation organized by medallion layer (Gold/Silver/Bronze).
"""

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dagster as dg


@dataclass
class AssetInfo:
    """Extracted information about a single asset."""

    key: str
    key_path: list[str]
    group: str | None
    layer: str  # bronze, silver, gold
    description: str | None
    metadata: dict[str, Any]
    partitions: list[str] | None
    partition_type: str | None  # 'static', 'multi', 'dynamic', None
    dependencies: list[str]
    source: str | None


@dataclass
class ScheduleInfo:
    """Extracted information about a schedule."""

    name: str
    cron_schedule: str
    description: str | None
    target: str  # Asset group or job name
    timezone: str
    status: str  # RUNNING or STOPPED


class AssetDocExtractor:
    """Extract documentation info from Dagster Definitions."""

    def __init__(self, defs: dg.Definitions):
        self.defs = defs
        self._assets_by_key: dict[str, dg.AssetsDefinition] = {}
        self._build_asset_index()

    def _build_asset_index(self) -> None:
        """Build index of assets by key for dependency lookup."""
        for asset in self.defs.assets or []:
            if isinstance(asset, dg.AssetsDefinition):
                for key in asset.keys:
                    self._assets_by_key[key.to_user_string()] = asset

    def extract_all(self) -> list[AssetInfo]:
        """Extract info from all assets in definitions."""
        assets = []
        for asset in self.defs.assets or []:
            if isinstance(asset, dg.AssetsDefinition):
                for key in asset.keys:
                    info = self._extract_asset_info(asset, key)
                    assets.append(info)
        return assets

    def _extract_asset_info(
        self, asset: dg.AssetsDefinition, key: dg.AssetKey
    ) -> AssetInfo:
        """Extract info from a single asset."""
        key_str = key.to_user_string()
        key_path = list(key.path)

        # Get metadata for this specific key
        metadata = dict(asset.metadata_by_key.get(key, {}))

        # Extract layer (default to 'bronze' if not specified)
        layer = metadata.pop("layer", "bronze")

        # Extract description
        description = metadata.pop("description", None)
        if not description:
            # Try to get from asset spec
            for spec in asset.specs:
                if spec.key == key and spec.description:
                    description = spec.description
                    break

        # Extract source
        source = metadata.pop("source", None)

        # Extract partition info
        partitions, partition_type = self._extract_partitions(asset)

        # Extract dependencies
        dependencies = self._extract_dependencies(asset, key)

        # Extract group
        group = None
        for spec in asset.specs:
            if spec.key == key:
                group = spec.group_name
                break

        return AssetInfo(
            key=key_str,
            key_path=key_path,
            group=group,
            layer=layer,
            description=description,
            metadata=metadata,
            partitions=partitions,
            partition_type=partition_type,
            dependencies=dependencies,
            source=source,
        )

    def _extract_partitions(
        self, asset: dg.AssetsDefinition
    ) -> tuple[list[str] | None, str | None]:
        """Extract partition keys and type from asset."""
        partitions_def = asset.partitions_def
        if partitions_def is None:
            return None, None

        if isinstance(partitions_def, dg.StaticPartitionsDefinition):
            keys = list(partitions_def.get_partition_keys())
            return keys, "static"

        if isinstance(partitions_def, dg.MultiPartitionsDefinition):
            # For multi-dimensional, return dimension info
            dims = []
            for dim_name, dim_def in partitions_def.partitions_defs:
                if isinstance(dim_def, dg.StaticPartitionsDefinition):
                    count = len(list(dim_def.get_partition_keys()))
                    dims.append(f"{dim_name}({count})")
                else:
                    dims.append(dim_name)
            return dims, "multi"

        if isinstance(partitions_def, dg.DynamicPartitionsDefinition):
            return [f"dynamic:{partitions_def.name}"], "dynamic"

        return None, None

    def _extract_dependencies(
        self, asset: dg.AssetsDefinition, key: dg.AssetKey
    ) -> list[str]:
        """Extract upstream dependencies for an asset."""
        deps = []
        for dep_key in asset.dependency_keys:
            deps.append(dep_key.to_user_string())
        return sorted(deps)

    def extract_schedules(self) -> list[ScheduleInfo]:
        """Extract info from all schedules in definitions."""
        schedules = []
        for schedule in self.defs.schedules or []:
            info = self._extract_schedule_info(schedule)
            schedules.append(info)
        return schedules

    def _extract_schedule_info(self, schedule: dg.ScheduleDefinition) -> ScheduleInfo:
        """Extract info from a single schedule."""
        # Determine target (asset group or job name)
        target = "unknown"
        if hasattr(schedule, "_target") and schedule._target:
            # Try to extract a cleaner target name
            target_obj = schedule._target
            if hasattr(target_obj, "resolvable_to_job"):
                job = target_obj.resolvable_to_job
                if hasattr(job, "selection") and hasattr(
                    job.selection, "selected_groups"
                ):
                    groups = job.selection.selected_groups
                    target = f"group:{', '.join(groups)}"
                elif hasattr(job, "name") and not job.name.startswith("__anonymous"):
                    target = f"job:{job.name}"
                else:
                    target = "assets"
        elif hasattr(schedule, "_job_name") and schedule._job_name:
            target = f"job:{schedule._job_name}"

        # Get default status
        status = "STOPPED"
        if hasattr(schedule, "default_status"):
            status = (
                schedule.default_status.name if schedule.default_status else "STOPPED"
            )

        return ScheduleInfo(
            name=schedule.name,
            cron_schedule=schedule.cron_schedule,
            description=schedule.description,
            target=target,
            timezone=schedule.execution_timezone or "UTC",
            status=status,
        )


class MarkdownRenderer:
    """Render asset documentation as markdown."""

    LAYER_EMOJI = {
        "gold": "🥇",
        "silver": "🥈",
        "bronze": "🥉",
    }

    LAYER_TITLES = {
        "gold": "Gold Layer (Published/Semantic)",
        "silver": "Silver Layer (Reference/Transformed)",
        "bronze": "Bronze Layer (Raw)",
    }

    LAYER_DESCRIPTIONS = {
        "gold": "Ready-to-use data with semantic partitions (country codes, tickers).",
        "silver": "Crosswalks, registries, and validated/transformed data.",
        "bronze": "Raw data from external APIs with source-native partitions.",
    }

    def __init__(
        self, assets: list[AssetInfo], schedules: list[ScheduleInfo] | None = None
    ):
        self.assets = assets
        self.schedules = schedules or []

    def render_inventory(self) -> str:
        """Render DATA_INVENTORY.md content."""
        lines = [
            "# Data Inventory",
            "",
            f"*Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]

        # Group by layer, ordered gold -> silver -> bronze
        for layer in ["gold", "silver", "bronze"]:
            layer_assets = [a for a in self.assets if a.layer == layer]
            if not layer_assets:
                continue

            emoji = self.LAYER_EMOJI[layer]
            title = self.LAYER_TITLES[layer]
            desc = self.LAYER_DESCRIPTIONS[layer]

            lines.append(f"## {emoji} {title}")
            lines.append("")
            lines.append(desc)
            lines.append("")

            # Table header
            lines.append("| Asset | Source | Partitions | Description |")
            lines.append("|-------|--------|------------|-------------|")

            # Sort assets by key
            for asset in sorted(layer_assets, key=lambda a: a.key):
                key = f"`{asset.key}`"
                source = asset.source or asset.group or "-"
                partitions = self._format_partitions(asset)
                desc = asset.description or "-"
                # Remove newlines and truncate long descriptions
                desc = " ".join(desc.split())
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                lines.append(f"| {key} | {source} | {partitions} | {desc} |")

            lines.append("")

        return "\n".join(lines)

    def render_lineage(self) -> str:
        """Render LINEAGE.md with grouped dependency trees.

        Format:
        - Gold Layer section with domain subheadings
        - Silver Layer section for intermediate assets (terminals not feeding gold)
        - Unused Assets section for orphans (no deps and no dependents)
        - Tree connectors (├── └──) for dependencies
        """
        lines = [
            "# Data Lineage",
            "",
            f"*Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]

        # Build index of assets by key
        assets_by_key = {a.key: a for a in self.assets}

        # Build reverse dependency map: asset_key -> list of assets that depend on it
        dependents: dict[str, list[str]] = {}
        for asset in self.assets:
            for dep in asset.dependencies:
                if dep not in dependents:
                    dependents[dep] = []
                dependents[dep].append(asset.key)

        # Find terminal nodes (assets with no downstream dependents)
        terminals = [a for a in self.assets if a.key not in dependents]

        # Separate terminals by layer
        gold_terminals = [a for a in terminals if a.layer == "gold"]
        silver_terminals = [a for a in terminals if a.layer == "silver"]
        bronze_terminals = [a for a in terminals if a.layer == "bronze"]

        # Identify unused assets (no deps and no dependents - true orphans)
        unused = [
            a for a in terminals if not a.dependencies and a.key not in dependents
        ]
        unused_keys = {a.key for a in unused}

        # Remove unused from terminal lists (they go in their own section)
        gold_terminals = [a for a in gold_terminals if a.key not in unused_keys]
        silver_terminals = [a for a in silver_terminals if a.key not in unused_keys]
        bronze_terminals = [a for a in bronze_terminals if a.key not in unused_keys]

        # Render Gold Layer
        if gold_terminals:
            lines.append("## Gold Layer")
            lines.append("")
            self._render_layer_section(lines, gold_terminals, assets_by_key)

        # Render Silver Layer (terminals that don't feed into gold)
        if silver_terminals:
            lines.append("## Silver Layer")
            lines.append("")
            self._render_layer_section(lines, silver_terminals, assets_by_key)

        # Render Bronze Layer (terminals that don't feed into anything)
        if bronze_terminals:
            lines.append("## Bronze Layer")
            lines.append("")
            self._render_layer_section(lines, bronze_terminals, assets_by_key)

        # Render Unused Assets (orphans with no deps and no dependents)
        if unused:
            lines.append("## Unused Assets")
            lines.append("")
            unused_keys_list = sorted([a.key for a in unused])
            lines.append(", ".join(f"`{k}`" for k in unused_keys_list))
            lines.append("")

        return "\n".join(lines)

    def _render_layer_section(
        self,
        lines: list[str],
        terminals: list[AssetInfo],
        assets_by_key: dict[str, AssetInfo],
    ) -> None:
        """Render a layer section with domain groupings."""
        # Group terminals by domain (second path component for gold, first for others)
        by_domain: dict[str, list[AssetInfo]] = {}
        for asset in terminals:
            domain = asset.key_path[1] if len(asset.key_path) >= 2 else "other"
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(asset)

        # Render each domain group
        for domain in sorted(by_domain.keys()):
            domain_assets = sorted(by_domain[domain], key=lambda a: a.key)

            # Domain subheading (title case)
            lines.append(f"### {domain.replace('_', ' ').title()}")
            lines.append("")

            # Render each asset in the domain
            for asset in domain_assets:
                lines.append("```")
                self._render_upstream_tree(lines, asset, assets_by_key, depth=0)
                lines.append("```")
                lines.append("")

    def _render_upstream_tree(
        self,
        lines: list[str],
        asset: AssetInfo,
        assets_by_key: dict[str, AssetInfo],
        depth: int,
    ) -> None:
        """Render asset and its upstream dependencies as a tree.

        Args:
            lines: Output lines to append to
            asset: Current asset to render
            assets_by_key: Index of all assets by key
            depth: Current indentation depth
        """
        indent = "  " * depth
        layer_marker = f"[{asset.layer}]"
        lines.append(f"{indent}{asset.key} {layer_marker}")

        deps = sorted(asset.dependencies)
        for i, dep_key in enumerate(deps):
            is_last = i == len(deps) - 1
            connector = "└── " if is_last else "├── "

            dep_asset = assets_by_key.get(dep_key)
            if dep_asset:
                # Render the dependency with its own upstream tree
                lines.append(f"{indent}{connector}{dep_asset.key} [{dep_asset.layer}]")
                # Recursively render the dependency's upstream deps
                if dep_asset.dependencies:
                    self._render_dep_subtree(
                        lines, dep_asset, assets_by_key, depth + 1, is_last
                    )
            else:
                # External dependency (not in our asset graph)
                lines.append(f"{indent}{connector}{dep_key} [external]")

    def _render_dep_subtree(
        self,
        lines: list[str],
        asset: AssetInfo,
        assets_by_key: dict[str, AssetInfo],
        depth: int,
        parent_is_last: bool,
    ) -> None:
        """Render a dependency's subtree with proper indentation."""
        deps = sorted(asset.dependencies)
        for i, dep_key in enumerate(deps):
            is_last = i == len(deps) - 1
            # Build prefix based on parent context
            prefix = "    " * depth

            connector = "└── " if is_last else "├── "

            dep_asset = assets_by_key.get(dep_key)
            if dep_asset:
                lines.append(f"{prefix}{connector}{dep_asset.key} [{dep_asset.layer}]")
                if dep_asset.dependencies:
                    self._render_dep_subtree(
                        lines, dep_asset, assets_by_key, depth + 1, is_last
                    )
            else:
                lines.append(f"{prefix}{connector}{dep_key} [external]")

    def render_readme(self) -> str:
        """Render overview README.md content."""
        # Count assets by layer
        counts = {"gold": 0, "silver": 0, "bronze": 0}
        for asset in self.assets:
            counts[asset.layer] = counts.get(asset.layer, 0) + 1

        lines = [
            "# Data Documentation",
            "",
            f"*Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "Auto-generated documentation for the actBI data pipeline.",
            "",
            "## Summary",
            "",
            "| Layer | Count |",
            "|-------|-------|",
            f"| 🥇 Gold | {counts['gold']} |",
            f"| 🥈 Silver | {counts['silver']} |",
            f"| 🥉 Bronze | {counts['bronze']} |",
            f"| **Total** | **{sum(counts.values())}** |",
            "",
            "## Documentation Files",
            "",
            "- [DATA_INVENTORY.md](DATA_INVENTORY.md) - Complete asset inventory by layer",
            "- [LINEAGE.md](LINEAGE.md) - Asset dependency relationships",
            f"- [SCHEDULES.md](SCHEDULES.md) - Automated refresh schedules ({len(self.schedules)} schedules)",
            "",
            "## Medallion Architecture",
            "",
            "### 🥇 Gold Layer",
            "Published, semantic assets ready for consumption. Use friendly partitions",
            "(country codes, tickers) and route to appropriate bronze sources.",
            "",
            "### 🥈 Silver Layer",
            "Reference data (crosswalks, registries) and transformed/validated data.",
            "Maps semantic identifiers to source-native IDs.",
            "",
            "### 🥉 Bronze Layer",
            "Raw data from external APIs. Partitioned by source-native identifiers",
            "(series IDs, CIKs, indicator codes).",
        ]

        return "\n".join(lines)

    def _format_partitions(self, asset: AssetInfo) -> str:
        """Format partition info for display."""
        if not asset.partitions:
            return "-"

        if asset.partition_type == "multi":
            # Multi-dimensional: show dimensions
            return " × ".join(asset.partitions)

        if asset.partition_type == "dynamic":
            return asset.partitions[0]

        # Static partitions: show count or abbreviated list
        if len(asset.partitions) <= 3:
            return ", ".join(asset.partitions)
        else:
            preview = ", ".join(asset.partitions[:2])
            return f"{preview}, ... ({len(asset.partitions)} total)"

    # Cron day-of-week mapping
    CRON_DAYS = {
        "0": "Sun",
        "1": "Mon",
        "2": "Tue",
        "3": "Wed",
        "4": "Thu",
        "5": "Fri",
        "6": "Sat",
        "7": "Sun",
    }

    def _format_cron(self, cron: str) -> str:
        """Convert cron expression to friendly format like 'Mon 2:00 AM'."""
        parts = cron.split()
        if len(parts) != 5:
            return cron

        minute, hour, _, _, dow = parts
        try:
            hour_int = int(hour)
            minute_int = int(minute)
            am_pm = "AM" if hour_int < 12 else "PM"
            hour_12 = hour_int % 12 or 12
            time_str = f"{hour_12}:{minute_int:02d} {am_pm}"
            day_str = self.CRON_DAYS.get(dow, dow)
            return f"{day_str} {time_str}"
        except ValueError:
            return cron

    def render_schedules(self) -> str:
        """Render SCHEDULES.md content."""
        lines = [
            "# Schedules",
            "",
            f"*Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
            "Automated data refresh schedules. All schedules start **STOPPED** by default.",
            "",
            "## Enable a Schedule",
            "",
            "```bash",
            "dg schedule start <schedule_name>",
            "```",
            "",
            "## Schedule Overview",
            "",
            "| Schedule | When | Target | Description |",
            "|----------|------|--------|-------------|",
        ]

        for schedule in sorted(self.schedules, key=lambda s: s.name):
            desc = schedule.description or "-"
            desc = " ".join(desc.split())  # Remove newlines
            if len(desc) > 55:
                desc = desc[:52] + "..."
            when = self._format_cron(schedule.cron_schedule)
            lines.append(f"| `{schedule.name}` | {when} | {schedule.target} | {desc} |")

        lines.append("")

        return "\n".join(lines)


def generate_docs(defs: dg.Definitions, output_dir: Path) -> None:
    """Generate all documentation files.

    Args:
        defs: Dagster Definitions object
        output_dir: Directory to write markdown files
    """
    # Extract asset and schedule info
    extractor = AssetDocExtractor(defs)
    assets = extractor.extract_all()
    schedules = extractor.extract_schedules()

    # Render markdown
    renderer = MarkdownRenderer(assets, schedules)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    (output_dir / "README.md").write_text(renderer.render_readme())
    (output_dir / "DATA_INVENTORY.md").write_text(renderer.render_inventory())
    (output_dir / "LINEAGE.md").write_text(renderer.render_lineage())
    (output_dir / "SCHEDULES.md").write_text(renderer.render_schedules())

    print(f"Generated documentation in {output_dir}")
    print("  - README.md")
    print("  - DATA_INVENTORY.md")
    print("  - LINEAGE.md")
    print("  - SCHEDULES.md")
