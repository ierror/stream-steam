SHELL := /bin/sh

PROJECT := config
PROJECT_DIR := $(abspath $(shell pwd))

pre_commit_all:
	pre-commit install
	pre-commit run --all-files
