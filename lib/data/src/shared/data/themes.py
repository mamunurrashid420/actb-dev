"""Financial themes for SEC XBRL data.

Themes provide a semantic layer that maps LLM-friendly categories to
SEC XBRL concept names. This allows LLMs to filter financial data by
high-level themes without needing to know specific XBRL concepts.

Usage:
    from shared.data.themes import FINANCIAL_THEMES, get_all_theme_concepts

    # Get all concepts across all themes
    concepts = get_all_theme_concepts()

    # Get concepts for specific themes
    from shared.data.themes import get_concepts_for_themes
    revenue_concepts = get_concepts_for_themes(['revenue', 'profitability'])

    # Build concept-to-theme mapping
    from shared.data.themes import get_concept_theme_mapping
    mapping = get_concept_theme_mapping()
    theme = mapping['NetIncomeLoss']  # Returns 'profitability'
"""

from dataclasses import dataclass


@dataclass
class FinancialTheme:
    """A semantic theme mapping to SEC XBRL concepts."""

    name: str
    description: str
    questions: list[str]
    concepts: list[str]


FINANCIAL_THEMES: dict[str, FinancialTheme] = {
    "profitability": FinancialTheme(
        name="profitability",
        description="Net income and operating performance metrics",
        questions=[
            "Is {company} profitable?",
            "What is {company}'s net income?",
            "How has {company}'s profitability changed?",
            "What is {company}'s operating income?",
        ],
        concepts=[
            "NetIncomeLoss",
            "NetIncomeLossAvailableToCommonStockholdersBasic",
            "NetIncomeLossAvailableToCommonStockholdersDiluted",
            "OperatingIncomeLoss",
            "GrossProfit",
            "ProfitLoss",
            "IncomeLossFromContinuingOperations",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ],
    ),
    "revenue": FinancialTheme(
        name="revenue",
        description="Sales and revenue recognition",
        questions=[
            "What is {company}'s revenue?",
            "How fast is {company} growing?",
            "What are {company}'s sales?",
        ],
        concepts=[
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueNet",
            "SalesRevenueGoodsNet",
            "SalesRevenueServicesNet",
        ],
    ),
    "balance_sheet": FinancialTheme(
        name="balance_sheet",
        description="Assets, liabilities, and equity totals",
        questions=[
            "What are {company}'s total assets?",
            "What are {company}'s total liabilities?",
            "What is {company}'s stockholders equity?",
            "What is {company}'s book value?",
        ],
        concepts=[
            "Assets",
            "AssetsCurrent",
            "AssetsNoncurrent",
            "Liabilities",
            "LiabilitiesCurrent",
            "LiabilitiesNoncurrent",
            "LiabilitiesAndStockholdersEquity",
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            "RetainedEarningsAccumulatedDeficit",
            "CommonStockValue",
            "AdditionalPaidInCapital",
        ],
    ),
    "cash_position": FinancialTheme(
        name="cash_position",
        description="Cash and cash equivalents on hand",
        questions=[
            "How much cash does {company} have?",
            "What is {company}'s cash position?",
            "What is {company}'s liquidity?",
        ],
        concepts=[
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
            "Cash",
            "RestrictedCash",
            "RestrictedCashAndCashEquivalents",
        ],
    ),
    "cash_flow_operations": FinancialTheme(
        name="cash_flow_operations",
        description="Operating cash flows and working capital adjustments",
        questions=[
            "What is {company}'s operating cash flow?",
            "Is {company} generating cash from operations?",
            "How much cash does {company} generate from its business?",
        ],
        concepts=[
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            "DepreciationDepletionAndAmortization",
            "DepreciationAndAmortization",
            "Depreciation",
            "AmortizationOfIntangibleAssets",
            "ShareBasedCompensation",
            "AllocatedShareBasedCompensationExpense",
            "DeferredIncomeTaxExpenseBenefit",
            "IncreaseDecreaseInAccountsReceivable",
            "IncreaseDecreaseInInventories",
            "IncreaseDecreaseInAccountsPayable",
            "IncreaseDecreaseInOperatingCapital",
        ],
    ),
    "cash_flow_investing": FinancialTheme(
        name="cash_flow_investing",
        description="CapEx, acquisitions, and asset purchases/sales",
        questions=[
            "How much is {company} spending on CapEx?",
            "What is {company}'s capital expenditure?",
            "Has {company} made any acquisitions?",
            "What is {company}'s investing cash flow?",
        ],
        concepts=[
            "NetCashProvidedByUsedInInvestingActivities",
            "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations",
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireBusinessesNetOfCashAcquired",
            "PaymentsToAcquireInvestments",
            "PaymentsToAcquireMarketableSecurities",
            "ProceedsFromSaleOfPropertyPlantAndEquipment",
            "ProceedsFromSaleOfInvestments",
            "ProceedsFromMaturitiesPrepaymentsAndCallsOfAvailableForSaleSecurities",
            "CapitalExpendituresIncurredButNotYetPaid",
        ],
    ),
    "cash_flow_financing": FinancialTheme(
        name="cash_flow_financing",
        description="Debt/equity issuance, dividends, and buybacks",
        questions=[
            "Is {company} raising or paying down debt?",
            "How much is {company} spending on buybacks?",
            "What dividends is {company} paying?",
            "What is {company}'s financing cash flow?",
        ],
        concepts=[
            "NetCashProvidedByUsedInFinancingActivities",
            "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations",
            "ProceedsFromIssuanceOfLongTermDebt",
            "ProceedsFromIssuanceOfCommonStock",
            "RepaymentsOfLongTermDebt",
            "RepaymentsOfShortTermDebt",
            "PaymentsForRepurchaseOfCommonStock",
            "PaymentsOfDividendsCommonStock",
            "PaymentsOfDividends",
            "DividendsCommonStockCash",
        ],
    ),
    "earnings_per_share": FinancialTheme(
        name="earnings_per_share",
        description="EPS and shares outstanding",
        questions=[
            "What is {company}'s EPS?",
            "What are {company}'s earnings per share?",
            "How many shares does {company} have outstanding?",
        ],
        concepts=[
            "EarningsPerShareBasic",
            "EarningsPerShareDiluted",
            "EarningsPerShareBasicAndDiluted",
            "WeightedAverageNumberOfSharesOutstandingBasic",
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "CommonStockSharesOutstanding",
            "CommonStockSharesIssued",
            "CommonStockSharesAuthorized",
        ],
    ),
    "debt_leverage": FinancialTheme(
        name="debt_leverage",
        description="Debt levels and interest costs",
        questions=[
            "How much debt does {company} have?",
            "What is {company}'s interest expense?",
            "Is {company} highly leveraged?",
            "What are {company}'s debt levels?",
        ],
        concepts=[
            "LongTermDebt",
            "LongTermDebtNoncurrent",
            "LongTermDebtCurrent",
            "ShortTermBorrowings",
            "DebtCurrent",
            "LongTermDebtAndCapitalLeaseObligations",
            "InterestExpense",
            "InterestPaidNet",
            "InterestPaid",
            "OperatingLeaseLiability",
            "OperatingLeaseLiabilityCurrent",
            "OperatingLeaseLiabilityNoncurrent",
        ],
    ),
    "shareholder_returns": FinancialTheme(
        name="shareholder_returns",
        description="Dividends and stock buybacks",
        questions=[
            "What dividends does {company} pay?",
            "How much is {company} returning to shareholders?",
            "What is {company}'s dividend per share?",
            "How much stock has {company} repurchased?",
        ],
        concepts=[
            "CommonStockDividendsPerShareDeclared",
            "CommonStockDividendsPerShareCashPaid",
            "DividendsCommonStockCash",
            "PaymentsOfDividendsCommonStock",
            "PaymentsForRepurchaseOfCommonStock",
            "StockRepurchasedAndRetiredDuringPeriodValue",
            "TreasuryStockValue",
            "TreasuryStockShares",
        ],
    ),
    "expenses": FinancialTheme(
        name="expenses",
        description="Operating costs, R&D, and SG&A",
        questions=[
            "What are {company}'s operating expenses?",
            "How much does {company} spend on R&D?",
            "What is {company}'s cost of goods sold?",
            "What are {company}'s SG&A expenses?",
        ],
        concepts=[
            "CostOfGoodsAndServicesSold",
            "CostOfRevenue",
            "CostOfGoodsSold",
            "OperatingExpenses",
            "GeneralAndAdministrativeExpense",
            "SellingGeneralAndAdministrativeExpense",
            "SellingAndMarketingExpense",
            "ResearchAndDevelopmentExpense",
            "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
        ],
    ),
    "taxes": FinancialTheme(
        name="taxes",
        description="Tax expense and effective rates",
        questions=[
            "What is {company}'s tax expense?",
            "What is {company}'s effective tax rate?",
            "How much does {company} pay in taxes?",
        ],
        concepts=[
            "IncomeTaxExpenseBenefit",
            "CurrentIncomeTaxExpenseBenefit",
            "DeferredIncomeTaxExpenseBenefit",
            "IncomeTaxesPaidNet",
            "EffectiveIncomeTaxRateContinuingOperations",
            "IncomeTaxesPaid",
            "DeferredTaxAssetsNet",
            "DeferredTaxLiabilitiesNet",
        ],
    ),
}


def list_themes() -> list[str]:
    """List all available financial themes."""
    return list(FINANCIAL_THEMES.keys())


def get_theme(theme: str) -> FinancialTheme:
    """Get a financial theme by name."""
    if theme not in FINANCIAL_THEMES:
        available = ", ".join(FINANCIAL_THEMES.keys())
        raise ValueError(f"Unknown theme '{theme}'. Available: {available}")
    return FINANCIAL_THEMES[theme]


def get_concepts_for_theme(theme: str) -> list[str]:
    """Get XBRL concepts for a single theme."""
    return get_theme(theme).concepts


def get_concepts_for_themes(themes: list[str]) -> list[str]:
    """Get unique XBRL concepts for multiple themes."""
    concepts: set[str] = set()
    for theme in themes:
        concepts.update(get_concepts_for_theme(theme))
    return sorted(concepts)


def get_all_theme_concepts() -> list[str]:
    """Get all unique XBRL concepts across all themes."""
    return get_concepts_for_themes(list(FINANCIAL_THEMES.keys()))


def get_concept_theme_mapping() -> dict[str, str]:
    """Build a concept-to-theme mapping.

    Note: Concepts can appear in multiple themes. This returns the first
    theme that contains each concept (in theme definition order).
    """
    mapping: dict[str, str] = {}
    for theme_name, theme in FINANCIAL_THEMES.items():
        for concept in theme.concepts:
            if concept not in mapping:
                mapping[concept] = theme_name
    return mapping


def get_all_questions() -> list[str]:
    """Get all example questions across all themes."""
    questions: list[str] = []
    for theme in FINANCIAL_THEMES.values():
        questions.extend(theme.questions)
    return questions


__all__ = [
    "FinancialTheme",
    "FINANCIAL_THEMES",
    "list_themes",
    "get_theme",
    "get_concepts_for_theme",
    "get_concepts_for_themes",
    "get_all_theme_concepts",
    "get_concept_theme_mapping",
    "get_all_questions",
]
