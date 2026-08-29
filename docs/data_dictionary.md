# Synthetic Data Dictionary

The canonical, machine-readable dictionary is generated as `data/raw/data_dictionary.csv`. It contains one row per field with these columns:

- `table_name`: owning table
- `field_name`: field name
- `data_type`: expected logical type
- `description`: business meaning in this fictional system
- `example_value`: synthetic example

Run `python generate_data.py` to regenerate the dictionary together with all five Parquet tables. All examples and entities are fictional and must not be interpreted as real operational identifiers or data.
