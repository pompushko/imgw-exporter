[![Docker](https://badgen.net/badge/icon/docker?icon=docker&label)](https://hub.docker.com/r/pompushko/imgw-exporter)

# Prometheus Exporter for IMGW-PIB (Institute of Meteorology and Water Management)

This project is a **Prometheus Exporter for IMGW-PIB** designed to collect and expose meteorological and hydrological data from the **Institute of Meteorology and Water Management - National Research Institute (IMGW-PIB)**. The exporter fetches real-time data provided by IMGW on weather conditions, water levels, and other environmental metrics across Poland, making this information available for monitoring and alerting in Prometheus.

Key features:
+ **Data Sources**: Collects data from IMGW's public API, including meteorological observations, water levels, temperature, precipitation, wind speed, and more.
+ **Metrics Exposure**: Exposes the collected data in a format compatible with Prometheus, allowing seamless integration with Grafana and other monitoring tools.
+ **Customizable Queries**: Allows users to specify the regions, stations, and types of data they wish to monitor, enabling targeted and efficient data collection.
+ **Alerting Capabilities**: Integrated with Prometheus’ alerting rules, enabling users to set up notifications for extreme weather conditions or critical environmental changes.

This project aims to provide a reliable and efficient way to monitor weather and water data in Poland, enhancing observability for research, environmental monitoring, and disaster preparedness efforts.

## Example of running in Docker
```yaml
  imgw-exporter:
    image: pompushko/imgw-exporter:latest
    environment:
      - STATION_ID=151160170,151170030,151160190,150170040,151170050
    ports:
      - "9634:8000"
    restart: always
    deploy:
      mode: global
```
## Prometheus target settings
```yaml
  - job_name: 'imgw-exporter'

    scrape_interval: 1m
  
    static_configs:
      - targets: ['imgw-exporter:9634']
```
