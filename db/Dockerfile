FROM postgres:12.3-alpine

# By adding scripts to the folder below, the container startup will execute automatically.
COPY create_mev_db.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/create_mev_db.sh