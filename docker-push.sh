#!/bin/sh
set -e

DOCKER_IMAGE="oxilor/dsm:latest"

docker build -t $DOCKER_IMAGE .

echo "Are you sure you want to push the image to Docker Hub?"
select yn in Yes No; do
  case $yn in
    Yes) docker push $DOCKER_IMAGE; break;;
    No) break;;
  esac
done

echo "Done."
