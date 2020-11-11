#!/bin/bash -ex

mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=$BUILD_TYPE -GNinja
ninja package
