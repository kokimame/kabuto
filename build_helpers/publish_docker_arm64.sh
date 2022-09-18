#!/bin/sh

# Use BuildKit, otherwise building on ARM fails
export DOCKER_BUILDKIT=1

# Replace / with _ to create a valid tag
TAG=$(echo "${BRANCH_NAME}" | sed -e "s/\//_/g")
TAG_PLOT=${TAG}_plot
TAG_FREQAI=${TAG}_freqai
TAG_PI="${TAG}_pi"

TAG_ARM=${TAG}_arm
TAG_PLOT_ARM=${TAG_PLOT}_arm
TAG_FREQAI_ARM=${TAG_FREQAI}_arm
CACHE_IMAGE=freqtradeorg/freqtrade_cache

echo "Running for ${TAG}"

# Add commit and commit_message to docker container
echo "${GITHUB_SHA}" > freqtrade_commit

if [ "${GITHUB_EVENT_NAME}" = "schedule" ]; then
    echo "event ${GITHUB_EVENT_NAME}: full rebuild - skipping cache"
    # Build regular image
    docker build -t freqtrade:${TAG_ARM} .

else
    echo "event ${GITHUB_EVENT_NAME}: building with cache"
    # Build regular image
    docker pull ${IMAGE_NAME}:${TAG_ARM}
    docker build --cache-from ${IMAGE_NAME}:${TAG_ARM} -t freqtrade:${TAG_ARM} .

fi

if [ $? -ne 0 ]; then
    echo "failed building multiarch images"
    return 1
fi
# Tag image for upload and next build step
docker tag freqtrade:$TAG_ARM ${CACHE_IMAGE}:$TAG_ARM

docker build --cache-from freqtrade:${TAG_ARM} --build-arg sourceimage=${CACHE_IMAGE} --build-arg sourcetag=${TAG_ARM} -t freqtrade:${TAG_PLOT_ARM} -f docker/Dockerfile.plot .
docker build --cache-from freqtrade:${TAG_ARM} --build-arg sourceimage=${CACHE_IMAGE} --build-arg sourcetag=${TAG_ARM} -t freqtrade:${TAG_FREQAI_ARM} -f docker/Dockerfile.freqai .

docker tag freqtrade:$TAG_PLOT_ARM ${CACHE_IMAGE}:$TAG_PLOT_ARM
docker tag freqtrade:$TAG_FREQAI_ARM ${CACHE_IMAGE}:$TAG_FREQAI_ARM

# Run backtest
docker run --rm -v $(pwd)/config_examples/config_bittrex.example.json:/freqtrade/config.json:ro -v $(pwd)/tests:/tests freqtrade:${TAG_ARM} backtesting --datadir /tests/testdata --strategy-path /tests/strategy/strats/ --strategy StrategyTestV3

if [ $? -ne 0 ]; then
    echo "failed running backtest"
    return 1
fi

docker images

# docker push ${IMAGE_NAME}
docker push ${CACHE_IMAGE}:$TAG_PLOT_ARM
docker push ${CACHE_IMAGE}:$TAG_FREQAI_ARM
docker push ${CACHE_IMAGE}:$TAG_ARM

# Create multi-arch image
# Make sure that all images contained here are pushed to github first.
# Otherwise installation might fail.
echo "create manifests"

docker manifest create --amend ${IMAGE_NAME}:${TAG} ${CACHE_IMAGE}:${TAG_ARM} ${IMAGE_NAME}:${TAG_PI} ${CACHE_IMAGE}:${TAG}
docker manifest push -p ${IMAGE_NAME}:${TAG}

docker manifest create ${IMAGE_NAME}:${TAG_PLOT} ${CACHE_IMAGE}:${TAG_PLOT_ARM} ${CACHE_IMAGE}:${TAG_PLOT}
docker manifest push -p ${IMAGE_NAME}:${TAG_PLOT}

docker manifest create ${IMAGE_NAME}:${TAG_FREQAI} ${CACHE_IMAGE}:${TAG_FREQAI_ARM} ${CACHE_IMAGE}:${TAG_FREQAI}
docker manifest push -p ${IMAGE_NAME}:${TAG_FREQAI}

# Tag as latest for develop builds
if [ "${TAG}" = "develop" ]; then
    docker manifest create ${IMAGE_NAME}:latest ${CACHE_IMAGE}:${TAG_ARM} ${IMAGE_NAME}:${TAG_PI} ${CACHE_IMAGE}:${TAG}
    docker manifest push -p ${IMAGE_NAME}:latest
fi

docker images

# Cleanup old images from arm64 node.
docker image prune -a --force --filter "until=24h"
