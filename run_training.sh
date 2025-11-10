#!/bin/zsh
cd /Users/shashi/sentiment-agent
source .venv312/bin/activate
/usr/local/bin/python3 train_models.py >> /Users/shashi/sentiment-agent/training.log 2>&1



