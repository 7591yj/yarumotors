SERVICES := $(shell find services -mindepth 1 -maxdepth 1 -type d)
P := 4

.PHONY: install fmt lint lint-fix test

install:
	@echo "Installing in all workspaces..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 install' -- {}

build:
	@echo "Building in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run build' -- {}

run:
	@echo "Running in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run run' -- {}

fmt:
	@echo "Formatting in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run format' -- {}

lint:
	@echo "Linting in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run lint' -- {}

lint-fix:
	@echo "Linting in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run lintfix' -- {}

test:
	@echo "Testing in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run test' -- {}
