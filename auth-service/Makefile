.PHONY: test test-unit test-integration test-connectivity test-predeploy install-deps clean

# Install Python dependencies
install-deps:
	pip install -r requirements.txt

# Run all tests
test: install-deps
	python -m pytest tests/ -v

# Run only connectivity and basic tests (fast)
test-connectivity: install-deps
	python -m pytest tests/test_connectivity.py tests/test_settings.py -v

# Run unit-style tests (no external dependencies)
test-unit: install-deps
	python -m pytest tests/test_error_handling.py -v

# Run integration tests (requires running service)
test-integration: install-deps
	python -m pytest tests/ -v --ignore=tests/test_connectivity.py

# Pre-deploy tests for Porter (fast, essential tests only)
test-predeploy: install-deps
	@echo "=== Running Pre-Deploy Tests ==="
	@echo "Testing connectivity and core functionality..."
	@if [ -z "$SUPABASE_URL" ]; then echo "ERROR: SUPABASE_URL not set"; exit 1; fi
	@if [ -z "$SUPABASE_ANON_KEY" ]; then echo "ERROR: SUPABASE_ANON_KEY not set"; exit 1; fi
	python -m pytest \
		tests/test_connectivity.py \
		tests/test_settings.py \
		tests/test_signup.py::TestSignup::test_signup_with_email_password_success \
		tests/test_token.py::TestToken::test_login_with_password_grant_json \
		tests/test_error_handling.py::TestErrorHandling::test_unauthorized_requests \
		-v --tb=short --disable-warnings

# Run tests with coverage and generate HTML report
test-coverage: install-deps
	python -m pytest tests/ --cov=. --cov-report=html --cov-report=term

# Run tests in parallel (faster)
test-parallel: install-deps
	python -m pytest tests/ -v -n auto

# Run tests with JSON output for CI/CD
test-ci: install-deps
	python -m pytest tests/ -v --json-report --json-report-file=test-report.json --html=test-report.html --self-contained-html

# Load test environment variables and run tests
test-with-env:
	@if [ -f .env.test ]; then \
		export $(cat .env.test | grep -v '^#' | xargs) && python -m pytest tests/ -v; \
	else \
		echo "No .env.test file found. Running with system environment variables."; \
		python -m pytest tests/ -v; \
	fi

# Run specific test categories
test-auth: install-deps
	python -m pytest tests/test_signup.py tests/test_token.py tests/test_user_management.py -v

test-admin: install-deps
	python -m pytest tests/test_admin.py -v

test-recovery: install-deps
	python -m pytest tests/test_password_recovery.py tests/test_magic_link.py tests/test_otp.py -v

# Clean up test artifacts
clean:
	rm -rf __pycache__/
	rm -rf tests/__pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -f test-report.json test-report.html coverage.xml
	find . -name "*.pyc" -delete

# Help
help:
	@echo "Available test targets:"
	@echo "  test              - Run all tests"
	@echo "  test-connectivity - Run connectivity tests only"
	@echo "  test-unit         - Run unit tests only" 
	@echo "  test-integration  - Run integration tests"
	@echo "  test-predeploy    - Run pre-deploy tests (for CI/CD)"
	@echo "  test-coverage     - Run tests with coverage report"
	@echo "  test-parallel     - Run tests in parallel"
	@echo "  test-ci           - Run tests with CI/CD output formats"
	@echo "  test-with-env     - Load .env.test and run tests"
	@echo "  test-auth         - Run authentication-related tests"
	@echo "  test-admin        - Run admin tests"
	@echo "  test-recovery     - Run recovery/magic link tests"
	@echo "  install-deps      - Install Python dependencies"
	@echo "  clean             - Clean up test artifacts"
