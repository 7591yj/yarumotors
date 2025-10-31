SERVICES := $(shell find services -mindepth 1 -maxdepth 1 -type d)
P := 4

.PHONY: install fmt lint test

install:
	@echo "Installing in all workspaces..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 install' -- {}

fmt:
	@echo "Formatting in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run format' -- {}

lint:
	@echo "Linting in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run lint' -- {}

test:
	@echo "Testing in parallel..."
	@echo "$(SERVICES)" | xargs -n1 -P $(P) -I{} bash -c 'echo "==> $$1"; mise --cd $$1 run test' -- {}
