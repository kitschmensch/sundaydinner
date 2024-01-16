#!/bin/bash

git fetch
git merge origin/main
pip install -r requirements.txt
python reminders.py