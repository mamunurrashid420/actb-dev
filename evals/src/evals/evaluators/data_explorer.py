"""DataExplorer-specific evaluators."""

from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from agents.data_explorer.schemas import DataExplorerInput, DataExplorerOutput


@dataclass
class AssetFound(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that a specific asset was found."""

    expected_asset: str

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        found_paths = [a.asset_path for a in ctx.output.assets_found]
        return 1.0 if self.expected_asset in found_paths else 0.0


@dataclass
class AssetPathContains(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that at least one found asset path contains a keyword."""

    keyword: str

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        keyword_lower = self.keyword.lower()
        for asset in ctx.output.assets_found:
            if keyword_lower in asset.asset_path.lower():
                return 1.0
        return 0.0


@dataclass
class RecommendedAssetCorrect(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that the recommended asset matches expected."""

    expected_asset: str

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        return 1.0 if ctx.output.recommended_asset == self.expected_asset else 0.0


@dataclass
class AssetCountInRange(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that number of assets found is within expected range."""

    min_count: int = 1
    max_count: int = 10

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        count = len(ctx.output.assets_found)
        if self.min_count <= count <= self.max_count:
            return 1.0
        return 0.0


@dataclass
class HasSampleData(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that sample data was retrieved."""

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        if ctx.output.sample_data is None:
            return 0.0
        return 1.0 if ctx.output.sample_data.row_count > 0 else 0.0


@dataclass
class SourceCorrect(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that recommended asset is from expected source."""

    expected_source: str

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        for asset in ctx.output.assets_found:
            if asset.asset_path == ctx.output.recommended_asset:
                return 1.0 if asset.source == self.expected_source else 0.0
        return 0.0


@dataclass
class RationaleContains(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that rationale mentions key concepts."""

    must_contain: list[str]

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        text = ctx.output.rationale.lower()
        matches = sum(1 for kw in self.must_contain if kw.lower() in text)
        return matches / len(self.must_contain) if self.must_contain else 1.0


@dataclass
class HasRecommendation(Evaluator[DataExplorerInput, DataExplorerOutput]):
    """Check that the agent made a recommendation."""

    async def evaluate(
        self, ctx: EvaluatorContext[DataExplorerInput, DataExplorerOutput]
    ) -> float:
        return 1.0 if ctx.output.recommended_asset is not None else 0.0
