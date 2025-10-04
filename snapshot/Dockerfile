FROM alpine:latest

COPY snapshot_data_*.sh .

# Keep the image alive when testing but do nothing when used as init source
CMD ["sh", "-c", "echo 'Snapshot image loaded. Use this image to initialize volumes on other systems.' && tail -f /dev/null"]
