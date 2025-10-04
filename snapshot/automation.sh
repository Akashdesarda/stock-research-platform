echo "[1/4] Running container and compressing snapshot data..."
docker run --name snapshot-temp \
  -v sra-shared-data:/snapshot \
  snapshot-init-base \
  sh /snapshot_data_compress.sh

echo "[2/4] Committing the container as a new image..."
docker commit snapshot-temp akashdesarda/srp-snapshot-data:latest

echo "[3/4] Pushing the image to Docker Hub..."
docker push akashdesarda/srp-snapshot-data:latest

echo "[4/4] Cleaning up temporary container..."
docker rm snapshot-temp

echo "Done. Image 'akashdesarda/srp-snapshot-data:latest' is pushed to Docker Hub."