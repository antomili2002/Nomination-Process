# Column names as they appear in the Excel Data sheet
SCENARIO_ID_COL   = "SCENARIO_ID"
SCENARIO_NAME_COL = "SCENARIO_NAME"
OUTPUT_TYPE_COL   = "OUTPUT_TYPE"
YEAR_COL          = "YEAR"
MONTH_COL         = "MONTH"
TARIFF_COL        = "TARIFF"
MACHINE_NAME_COL  = "MACHINE_NAME"
POWER_POS_COL     = "POWER_POS__GWH"
IV_COL            = "INTRINSIC_VALUE__CUR"
EV_COL            = "EXTRINSIC_VALUE"
IV_INCL_HEAT_COSTS_COL = "IV_INCL_HEAT_COSTS"
HEAT_PRODUCTION_COL = "HEAT_PRODUCTION__GWH"

# Metric columns aggregated in reports
METRIC_COLS = [
    POWER_POS_COL,
    IV_COL,
    EV_COL,
    IV_INCL_HEAT_COSTS_COL,
    HEAT_PRODUCTION_COL,
]

# Minimum columns required in the Data sheet
REQUIRED_DATA_COLS = [
    SCENARIO_ID_COL,
    SCENARIO_NAME_COL,
    OUTPUT_TYPE_COL,
    YEAR_COL,
    MONTH_COL,
    TARIFF_COL,
    MACHINE_NAME_COL,
    POWER_POS_COL,
    IV_COL,
    EV_COL,
    IV_INCL_HEAT_COSTS_COL,
    HEAT_PRODUCTION_COL,
]

# Value in the first column of the Info sheet header row
INFO_HEADER_SENTINEL = "Scenario Name"

# Info sheet column names (after header row is found)
INFO_COL_SCENARIO_NAME = "Scenario Name"
INFO_COL_MARKET_AREA   = "Market Area"
INFO_COL_SCENARIO_TYPE = "Scenario Type"
INFO_COL_STATUS        = "Status"
INFO_COL_SCENARIO_ID   = "Scenario ID"
