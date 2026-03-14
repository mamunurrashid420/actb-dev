# Data Lineage

*Generated: 2026-01-22 18:59*

## Gold Layer

### Agriculture

```
gold/agriculture/weather/daily [gold]
└── bronze/nasa_power/daily [bronze]
```

```
gold/agriculture/weather/monthly [gold]
└── bronze/nasa_power/monthly [bronze]
```

### Climate

```
gold/climate/precipitation/total [gold]
├── bronze/noaa/daily [bronze]
└── silver/reference/noaa_locations [silver]
```

```
gold/climate/temperature/average [gold]
├── bronze/noaa/daily [bronze]
└── silver/reference/noaa_locations [silver]
```

### Companies

```
gold/companies/financials/annual_reports [gold]
├── silver/sec/company_registry [silver]
    └── bronze/sec/sec_filer_registry [bronze]
└── silver/sec/form_10k_sections [silver]
    └── bronze/sec/form_10k_text [bronze]
        ├── bronze/sec/submissions [bronze]
            └── bronze/sec/submissions_download [bronze]
        └── silver/sec/company_registry [silver]
            └── bronze/sec/sec_filer_registry [bronze]
```

```
gold/companies/financials/quarterly_reports [gold]
├── silver/sec/company_registry [silver]
    └── bronze/sec/sec_filer_registry [bronze]
└── silver/sec/form_10q_sections [silver]
    └── bronze/sec/form_10q_text [bronze]
        ├── bronze/sec/submissions [bronze]
            └── bronze/sec/submissions_download [bronze]
        └── silver/sec/company_registry [silver]
            └── bronze/sec/sec_filer_registry [bronze]
```

```
gold/companies/insider/insider_activity [gold]
├── silver/sec/company_registry [silver]
    └── bronze/sec/sec_filer_registry [bronze]
└── silver/sec/form_4_transactions [silver]
    └── bronze/sec/form_4 [bronze]
        ├── bronze/sec/submissions [bronze]
            └── bronze/sec/submissions_download [bronze]
        └── silver/sec/company_registry [silver]
            └── bronze/sec/sec_filer_registry [bronze]
```

### Economic

```
gold/economic/fiscal/government_debt [gold]
└── bronze/world_bank/timeseries [bronze]
```

```
gold/economic/growth/gdp [gold]
├── bronze/fred/series [bronze]
    └── bronze/fred/series_registry [bronze]
└── bronze/world_bank/timeseries [bronze]
```

```
gold/economic/labor_market/job_openings [gold]
├── bronze/bls/all_series [bronze]
└── silver/reference/indicator_id_crosswalk [silver]
```

```
gold/economic/labor_market/unemployment [gold]
├── bronze/fred/series [bronze]
    └── bronze/fred/series_registry [bronze]
└── bronze/world_bank/timeseries [bronze]
```

```
gold/economic/monetary/interest_rate [gold]
├── bronze/fred/series [bronze]
    └── bronze/fred/series_registry [bronze]
└── bronze/world_bank/timeseries [bronze]
```

```
gold/economic/prices/inflation [gold]
├── bronze/fred/series [bronze]
    └── bronze/fred/series_registry [bronze]
└── bronze/world_bank/timeseries [bronze]
```

```
gold/economic/trade/balance [gold]
└── bronze/world_bank/timeseries [bronze]
```

### Institutions

```
gold/institutions/portfolio/holdings [gold]
├── silver/sec/form_13f_holdings [silver]
    ├── bronze/sec/form_13f [bronze]
        ├── bronze/sec/submissions [bronze]
            └── bronze/sec/submissions_download [bronze]
        └── silver/sec/institution_registry [silver]
            └── bronze/sec/sec_filer_registry [bronze]
    └── bronze/sec/form_13f_bulk [bronze]
└── silver/sec/institution_registry [silver]
    └── bronze/sec/sec_filer_registry [bronze]
```

### Sec

```
gold/sec/company_profiles [gold]
├── bronze/sec/sec_filer_registry [bronze]
└── silver/sec/fsds_company_metadata [silver]
    └── bronze/sec/fsds [bronze]
```

```
gold/sec/financials [gold]
├── bronze/sec/sec_filer_registry [bronze]
├── silver/sec/company_facts [silver]
    └── bronze/sec/company_facts_download [bronze]
└── silver/sec/xbrl_taxonomy [silver]
    └── bronze/sec/xbrl_taxonomy_raw [bronze]
```

```
gold/sec/segments [gold]
├── bronze/sec/sec_filer_registry [bronze]
└── silver/sec/fsds_segments [silver]
    └── bronze/sec/fsds [bronze]
```

## Silver Layer

### Bea

```
silver/bea/nipa_data [silver]
├── bronze/bea/nipa_bulk [bronze]
└── bronze/bea/nipa_current [bronze]
```

### Sec

```
silver/sec/form_10k_financials [silver]
├── bronze/sec/sec_filer_registry [bronze]
└── silver/sec/company_facts [silver]
    └── bronze/sec/company_facts_download [bronze]
```

```
silver/sec/form_10q_financials [silver]
├── bronze/sec/sec_filer_registry [bronze]
└── silver/sec/company_facts [silver]
    └── bronze/sec/company_facts_download [bronze]
```

```
silver/sec/fsds_financials [silver]
└── bronze/sec/fsds [bronze]
```

```
silver/sec/fsds_footnotes [silver]
└── bronze/sec/fsds [bronze]
```

```
silver/sec/fsds_subsidiaries [silver]
└── bronze/sec/fsds [bronze]
```

### Usda

```
silver/usda/esr_data [silver]
└── bronze/usda/esr_exports [bronze]
    └── bronze/usda/esr_commodities [bronze]
```

```
silver/usda/gats_census_data [silver]
├── bronze/usda/gats_census_exports [bronze]
    └── bronze/usda/gats_countries [bronze]
├── bronze/usda/gats_census_imports [bronze]
    └── bronze/usda/gats_countries [bronze]
└── bronze/usda/gats_census_reexports [bronze]
    └── bronze/usda/gats_countries [bronze]
```

## Bronze Layer

### Bls

```
bronze/bls/cpi [bronze]
└── bronze/bls/cpi_download [bronze]
```

```
bronze/bls/employment [bronze]
└── bronze/bls/employment_download [bronze]
```

```
bronze/bls/jolts [bronze]
└── bronze/bls/jolts_download [bronze]
```

```
bronze/bls/labor_force [bronze]
└── bronze/bls/labor_force_download [bronze]
```

### Ecb

```
silver/ecb/exchange_rates [bronze]
└── bronze/ecb/exchange_rates [bronze]
```

### Patents

```
bronze/patents/abstracts [bronze]
└── bronze/patents/abstracts_download [bronze]
```

```
bronze/patents/assignees [bronze]
└── bronze/patents/assignees_download [bronze]
```

```
bronze/patents/citations [bronze]
└── bronze/patents/citations_download [bronze]
```

```
bronze/patents/cpc_current [bronze]
└── bronze/patents/cpc_current_download [bronze]
```

```
bronze/patents/cpc_titles [bronze]
└── bronze/patents/cpc_titles_download [bronze]
```

```
bronze/patents/inventors [bronze]
└── bronze/patents/inventors_download [bronze]
```

```
bronze/patents/patents [bronze]
└── bronze/patents/patents_download [bronze]
```

### Usda

```
bronze/usda/commodities [bronze]
└── bronze/usda/psd_bulk [bronze]
```

```
bronze/usda/countries [bronze]
└── bronze/usda/psd_bulk [bronze]
```

```
silver/usda/psd_data [bronze]
├── bronze/usda/psd_bulk [bronze]
└── bronze/usda/psd_current [bronze]
```

## Unused Assets

`bronze/noaa/annual`, `bronze/noaa/monthly`, `bronze/usda/esr_countries`, `bronze/usda/esr_regions`, `bronze/usda/esr_units`, `bronze/usda/gats_commodities`, `bronze/usda/gats_customs_districts`, `bronze/usda/gats_hs6_commodities`, `bronze/usda/gats_regions`, `bronze/usda/gats_units`, `bronze/usda/gats_untrade_exports`, `bronze/usda/gats_untrade_imports`, `bronze/usda/gats_untrade_reexports`, `silver/reference/nasa_power_location_registry`, `silver/reference/nasa_power_variable_crosswalk`, `silver/reference/noaa_stations`, `silver/reference/noaa_variables`
