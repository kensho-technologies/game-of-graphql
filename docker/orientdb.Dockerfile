FROM orientdb:2.2.37

ENV ORIENTDB_GAME_OF_THRONES_DB_URL https://orientdb.com/public-databases/GamesOfThrones.zip
ENV DB_ZIP_FILE_PATH /orientdb/GamesOfThrones.zip

# Update the installed CA certs and OpenSSL before downloading over HTTPS.
RUN apt-get update && \
    apt-get install -y ca-certificates openssl wget && \
    update-ca-certificates && \
    wget "$ORIENTDB_GAME_OF_THRONES_DB_URL" -O "$DB_ZIP_FILE_PATH"
RUN echo "3c968079d534a23a7cbba86a56d282555cfccb76832a518f61c028e59293f0e9 " \
         "GamesOfThrones.zip" | sha256sum -c -

# There appears to be a docker bug that prevents unzipping into a directory
# that is simultaneously marked as a volume in the image.
# Instead, we unzip when the container is executed.
CMD cd /orientdb/databases && \
    mkdir -p /orientdb/databases/GamesOfThrones && \
    rm -rf /orientdb/databases/GamesOfThrones/* && \
    cd ./GamesOfThrones && \
    unzip "$DB_ZIP_FILE_PATH" && \
    server.sh
