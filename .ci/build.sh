#!/bin/bash -ex

# set version
if [ -z "$GIT_TAG_NAME" ]; then
  export PV_VERSION="0+git$(date +'%Y%m%d')"
else
  export PV_VERSION="${GIT_TAG_NAME/v/}"
fi

mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=$BUILD_TYPE -GNinja
ninja package
