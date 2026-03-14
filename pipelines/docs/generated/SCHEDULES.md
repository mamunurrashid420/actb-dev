# Schedules

*Generated: 2026-01-22 18:59*

Automated data refresh schedules. All schedules start **STOPPED** by default.

## Enable a Schedule

```bash
dg schedule start <schedule_name>
```

## Schedule Overview

| Schedule | When | Target | Description |
|----------|------|--------|-------------|
| `daily_sec_form4_refresh` | * 6:00 AM | job:sec_form4_refresh | Refresh Form 4 insider trading data daily (current m... |
| `monthly_usda_registry_refresh` | * 2:00 AM | assets | Refresh USDA commodity and country registries monthly |
| `quarterly_bea_bulk_refresh` | * 3:00 AM | assets | Download BEA NIPA bulk data quarterly (catches GDP r... |
| `quarterly_fsds_refresh` | * 3:00 AM | job:sec_fsds_refresh | Download SEC Financial Statement Data Sets quarterly... |
| `quarterly_usda_bulk_refresh` | * 3:00 AM | assets | Download USDA PSD bulk data quarterly (catches histo... |
| `weekly_agriculture_refresh` | Mon 5:00 AM | group:agriculture_indicators | Refresh published agriculture weather indicators eve... |
| `weekly_bea_current_refresh` | Mon 5:00 AM | assets | Fetch current-year BEA NIPA data weekly via API (GDP... |
| `weekly_bls_refresh` | Fri 7:00 AM | group:bls | Fetch BLS labor market data (job openings, wages, et... |
| `weekly_combined_indicators` | Mon 4:00 AM | group:country_indicators | Refresh country-level economic indicators every Mond... |
| `weekly_ecb_exchange_rates_refresh` | Mon 3:00 AM | group:ecb | Fetch ECB exchange rates weekly (EUR rates for ~30 c... |
| `weekly_fiscal_indicators` | Mon 4:00 AM | group:fiscal_indicators | Refresh fiscal indicators (government debt) every Mo... |
| `weekly_fred_refresh` | Mon 2:00 AM | group:fred | Fetch FRED economic data (GDP, unemployment, CPI) ev... |
| `weekly_monetary_indicators` | Mon 4:00 AM | group:monetary_indicators | Refresh monetary indicators (interest rate) every Mo... |
| `weekly_nasa_power_refresh` | Mon 3:00 AM | group:nasa_power | Fetch NASA POWER agricultural weather data for all c... |
| `weekly_sec_10k_refresh` | Mon 2:00 AM | job:sec_10k_refresh | Refresh 10-K annual reports weekly (current year par... |
| `weekly_sec_10q_refresh` | Mon 2:00 AM | job:sec_10q_refresh | Refresh 10-Q quarterly reports weekly (current quart... |
| `weekly_sec_13f_refresh` | Mon 2:00 AM | job:sec_13f_refresh | Refresh 13-F institutional holdings weekly (current ... |
| `weekly_sec_bulk_refresh` | Sun 2:00 AM | job:sec_bulk_downloads_refresh | Download SEC bulk data files (submissions.zip + comp... |
| `weekly_sec_registry_refresh` | Sun 1:00 AM | job:sec_registry_refresh | Refresh SEC filer registry and filtered registries w... |
| `weekly_usda_current_refresh` | Mon 4:00 AM | assets | Fetch current-year USDA PSD data weekly via API (rol... |
| `weekly_world_bank_refresh` | Sun 2:00 AM | group:world_bank | Fetch World Bank country indicators (20 countries × ... |
