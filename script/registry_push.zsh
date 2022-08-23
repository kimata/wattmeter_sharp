#!/usr/bin/env zsh

NAME=wattmeter_sharp
REGISTRY=registry.green-rabbit.net/library

git push
docker build . -t ${NAME}
docker tag ${NAME} ${REGISTRY}/${NAME}
docker push ${REGISTRY}/${NAME}
