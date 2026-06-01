# csv-transformer

A command-line tool for transforming and filtering CSV files — no Excel or Python skills required.

## Features

- Filter rows by column value
- Select specific columns to keep
- Sort by multiple columns (ascending/descending)
- Export results to CSV or JSON

## Installation

```bash
pip install csv-transformer
```

## Usage

```bash
# Filter rows where status is 'active'
csv-transformer filter input.csv --col status --value active -o output.csv

# Select specific columns
csv-transformer select input.csv --cols id,name,email -o output.csv

# Sort by multiple columns (date ascending, amount descending)
csv-transformer sort input.csv --by date,amount --desc amount -o sorted.csv

# Chain operations
csv-transformer filter input.csv --col region --value KR \
  | csv-transformer select --cols id,name,amount \
  | csv-transformer sort --by amount --desc > result.csv
```

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)
