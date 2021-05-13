#!/usr/bin/env bash
# Fail on non-zero exit and echo the commands

pytest --doctest-modules --cov=skimage --pyargs skimage

flake8 --exit-zero --exclude=test_* skimage doc/examples viewer_examples

echo Build or run examples
python -m pip install --pre -r ./requirements/docs.txt
python -m pip list
tools/build_versions.py

echo Test examples
for f in doc/examples/*/*.py; do
    python "${f}"
    if [ $? -ne 0 ]; then
      exit 1
    fi
done
