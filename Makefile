GO ?= /opt/homebrew/Cellar/go/1.27.1/bin/go
GO_BIN := $(dir $(GO))

.PHONY: setup setup-dev dev test-dev

setup: setup-dev

setup-dev:
	@test -x "$(GO)" || (printf 'Go was not found at %s. Set GO=/path/to/go.\n' "$(GO)"; exit 1)
	@version="$$($(GO) version)"; case "$$version" in *"go1.27."*) printf '%s\n' "$$version" ;; *) printf 'Go 1.27 is required; found %s\n' "$$version"; exit 1 ;; esac

dev: setup-dev
	PATH="$(GO_BIN):$$PATH" $(GO) -C dev run .

test-dev: setup-dev
	PATH="$(GO_BIN):$$PATH" $(GO) -C dev test ./...
