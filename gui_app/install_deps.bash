#!/usr/bin/env bash

cd "$(dirname "$0")"
cat requirements.txt | xargs npm install -g