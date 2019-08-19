#!/bin/bash

USAGE="Usage: $(basename $0) [docs, image]"

if [[ $# -ne 0 && "$1" != "docs" && "$1" != "image" ]]; then
  echo "Invalid arguments. ${USAGE}"
  exit 1
fi

IMAGE=caplena/caplena-api

if [[ "$1" == "docs" ]]; then
  cd docs && make html && cd ..
else
  docker build -t $IMAGE .
fi
