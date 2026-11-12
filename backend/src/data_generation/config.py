
from pathlib import Path
from datetime import date

# -----------------------------------
# 1. Project Configuration
# -----------------------------------

RANDOM_SEED = 42

# -----------------------------------
# 2. Dataset Sizes
# -----------------------------------

NUM_BRANCHES = 5
NUM_WAREHOUSES = 3
NUM_PRODUCTS = 100
NUM_CUSTOMERS = 1_000
NUM_SUPPLIERS = 10

NUM_SALES_LINES = 20_000

# -----------------------------------
# 3. Data Generation Period
# -----------------------------------

START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 12, 31)

# -----------------------------------
# 4. Project Paths
# -----------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Create output directory if it does not exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
[]