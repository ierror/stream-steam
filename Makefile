SHELL := /bin/sh

PROJECT := config
PROJECT_DIR := $(abspath $(shell pwd))

release:
	git commit -m "bump v$(VERSION)" README.rst
	git checkout master
	git merge develop -m "bump v$(VERSION)"
	git push origin master
	git tag v$(VERSION)
	git push origin v$(VERSION)
	git checkout develop

pre_commit_all:
	pre-commit install
	pre-commit run --all-files
