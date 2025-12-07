FROM busybox
ARG API_VERSION
ENV API_VERSION=$API_VERSION
RUN mkdir -p /usr/src/code/
WORKDIR /usr/src/code
COPY backend_$API_VERSION.zip .
RUN cp /usr/src/code/backend_$API_VERSION.zip backend_latest.zip
ENTRYPOINT ["cp", "-a", "--remove-destination", "/usr/src/code/.", "/backend_code/"]
