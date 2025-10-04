Write-Host "[1/4] Running container and compressing snapshot data from docker volume..."
docker run --name snapshot-temp `
  -v sra-shared-data:/snapshot `
  snapshot-init-base `
  sh /snapshot_data_compress.sh

Write-Host "[2/4] Committing the container as a new image..."
docker commit snapshot-temp akashdesarda/srp-snapshot-data:latest

Write-Host "[3/4] Pushing the image to Docker Hub..."
docker push akashdesarda/srp-snapshot-data:latest

Write-Host "[4/4] Cleaning up temporary container..."
docker rm snapshot-temp

Write-Host "Done. Image 'akashdesarda/srp-snapshot-data:latest' is pushed to Docker Hub."