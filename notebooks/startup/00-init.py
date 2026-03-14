"""actBI notebook initialization."""

import os

import pandas as pd
from IPython.core.interactiveshell import InteractiveShell

import shared.data as data

# Configure pandas
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 200)

# Display all expressions, not just the last
InteractiveShell.ast_node_interactivity = "all"

# Set default environment
data.use_env("local")

print(f"actBI initialized. Data: {os.environ['ACTBI_DATA_PATH']}")
print("Available: pd, np, duckdb, data")
