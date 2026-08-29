-- Materialize the five reproducible synthetic Parquet datasets in DuckDB.
DROP VIEW IF EXISTS exception_analysis;
DROP VIEW IF EXISTS driver_performance;
DROP VIEW IF EXISTS daily_regional_performance;
DROP VIEW IF EXISTS station_performance;
DROP VIEW IF EXISTS dsp_performance;
DROP VIEW IF EXISTS route_performance;

CREATE OR REPLACE TABLE stations AS
SELECT * FROM read_parquet('data/raw/stations.parquet');

CREATE OR REPLACE TABLE delivery_service_providers AS
SELECT * FROM read_parquet('data/raw/delivery_service_providers.parquet');

CREATE OR REPLACE TABLE drivers AS
SELECT * FROM read_parquet('data/raw/drivers.parquet');

CREATE OR REPLACE TABLE routes AS
SELECT * FROM read_parquet('data/raw/routes.parquet');

CREATE OR REPLACE TABLE deliveries AS
SELECT * FROM read_parquet('data/raw/deliveries.parquet');

CREATE INDEX idx_routes_route_id ON routes(route_id);
CREATE INDEX idx_deliveries_route_id ON deliveries(route_id);
CREATE INDEX idx_deliveries_service_date ON deliveries(service_date);
