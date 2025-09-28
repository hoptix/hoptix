#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="predeploy"
VERBOSE=false
COVERAGE=false
PARALLEL=false
OUTPUT_FORMAT="terminal"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Test type: all, predeploy, unit, integration, connectivity, auth, admin, recovery (default: predeploy)"
    echo "  -v, --verbose          Enable verbose output"
    echo "  -c, --coverage         Run with coverage report"
    echo "  -p, --parallel         Run tests in parallel"
    echo "  -f, --format FORMAT    Output format: terminal, json, html (default: terminal)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                     # Run predeploy tests"
    echo "  $0 -t all -c           # Run all tests with coverage"
    echo "  $0 -t connectivity -v  # Run connectivity tests with verbose output"
    echo "  $0 -t auth -p          # Run auth tests in parallel"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check if we're in a container
is_container() {
    [ -f /.dockerenv ] || [ -n "${CONTAINER}" ] || [ -n "${KUBERNETES_SERVICE_HOST}" ] || [ "$(id -u)" = "0" ] || [ -f /app/auth-service-server ]
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    # Check if we're in a container or externally managed environment
    if is_container; then
        # In container, use --break-system-packages
        print_status "Container environment detected, using --break-system-packages"
        pip3 install --break-system-packages -r requirements.txt
    else
        # For local development, prefer virtual environment
        if [ ! -d ".venv" ]; then
            print_status "Creating virtual environment for local testing..."
            python3 -m venv .venv
        fi
        
        print_status "Using virtual environment"
        source .venv/bin/activate
        pip install -r requirements.txt
        
        if [ $? -eq 0 ]; then
            print_success "Dependencies installed successfully in virtual environment"
        else
            print_error "Failed to install dependencies in virtual environment"
            exit 1
        fi
    fi
}

# Function to check environment variables
check_environment() {
    print_status "Checking environment variables..."
    
    local required_vars=()
    local missing_vars=()
    
    # Check test type to determine required variables
    case $TEST_TYPE in
        predeploy|connectivity|integration|all)
            required_vars=("TEST_SUPABASE_URL" "TEST_SUPABASE_ANON_KEY")
            ;;
        admin|recovery)
            required_vars=("TEST_SUPABASE_URL" "TEST_SUPABASE_ANON_KEY" "TEST_SUPABASE_SERVICE_ROLE_KEY")
            ;;
    esac
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            print_error "  - $var"
        done
        exit 1
    fi
    
    print_success "Environment variables check passed"
}

# Function to wait for service to be ready (if running in container)
wait_for_service() {
    if [ -n "${TEST_BASE_URL}" ]; then
        print_status "Waiting for service to be ready at ${TEST_BASE_URL}..."
        
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -s "${TEST_BASE_URL}/health" > /dev/null 2>&1; then
                print_success "Service is ready!"
                return 0
            fi
            
            print_status "Attempt $attempt/$max_attempts - Service not ready yet, waiting..."
            sleep 2
            ((attempt++))
        done
        
        print_error "Service failed to become ready after $max_attempts attempts"
        exit 1
    fi
}

# Function to build pytest command
build_pytest_command() {
    # Determine the correct Python command
    local python_cmd=""
    
    # Use virtual environment python if it exists
    if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
        python_cmd=".venv/bin/python"
    else
        # Check for python3 first, then python
        if command -v python3 >/dev/null 2>&1; then
            python_cmd="python3"
        elif command -v python >/dev/null 2>&1; then
            python_cmd="python"
        else
            print_error "No Python interpreter found!"
            exit 1
        fi
    fi
    
    local cmd="$python_cmd -m pytest"
    local args=()
    
    # Add test paths based on type
    case $TEST_TYPE in
        all)
            args+=("tests/")
            ;;
        predeploy)
            args+=("tests/test_connectivity.py")
            args+=("tests/test_settings.py")
            args+=("tests/test_signup.py::TestSignup::test_signup_with_email_password_success")
            args+=("tests/test_token.py::TestToken::test_login_with_password_grant_json")
            args+=("tests/test_error_handling.py::TestErrorHandling::test_unauthorized_requests")
            ;;
        unit)
            args+=("tests/test_error_handling.py")
            ;;
        integration)
            args+=("tests/")
            args+=("--ignore=tests/test_connectivity.py")
            ;;
        connectivity)
            args+=("tests/test_connectivity.py")
            args+=("tests/test_settings.py")
            ;;
        auth)
            args+=("tests/test_signup.py")
            args+=("tests/test_token.py")
            args+=("tests/test_user_management.py")
            ;;
        admin)
            args+=("tests/test_admin.py")
            ;;
        recovery)
            args+=("tests/test_password_recovery.py")
            args+=("tests/test_magic_link.py")
            args+=("tests/test_otp.py")
            ;;
        *)
            print_error "Unknown test type: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # Add common options
    if [ "$VERBOSE" = true ]; then
        args+=("-v")
    fi
    
    if [ "$TEST_TYPE" = "predeploy" ]; then
        args+=("--tb=short")
        args+=("--disable-warnings")
    fi
    
    # Add coverage options
    if [ "$COVERAGE" = true ]; then
        args+=("--cov=.")
        case $OUTPUT_FORMAT in
            html)
                args+=("--cov-report=html")
                args+=("--cov-report=term")
                ;;
            json)
                args+=("--cov-report=json")
                ;;
            *)
                args+=("--cov-report=term")
                ;;
        esac
    fi
    
    # Add parallel execution
    if [ "$PARALLEL" = true ]; then
        args+=("-n" "auto")
    fi
    
    # Add output format options
    case $OUTPUT_FORMAT in
        json)
            args+=("--json-report")
            args+=("--json-report-file=test-report.json")
            ;;
        html)
            args+=("--html=test-report.html")
            args+=("--self-contained-html")
            ;;
    esac
    
    echo "$cmd ${args[*]}"
}

# Function to run tests
run_tests() {
    local pytest_cmd
    pytest_cmd=$(build_pytest_command)
    
    print_status "Running $TEST_TYPE tests..."
    print_status "Command: $pytest_cmd"
    
    if eval "$pytest_cmd"; then
        print_success "Tests passed!"
        return 0
    else
        print_error "Tests failed!"
        return 1
    fi
}

# Function to generate test report summary
generate_summary() {
    print_status "Test Summary:"
    echo "  Test Type: $TEST_TYPE"
    echo "  Verbose: $VERBOSE"
    echo "  Coverage: $COVERAGE"
    echo "  Parallel: $PARALLEL"
    echo "  Output Format: $OUTPUT_FORMAT"
    
    if [ "$COVERAGE" = true ] && [ -f "htmlcov/index.html" ]; then
        print_status "Coverage report generated: htmlcov/index.html"
    fi
    
    if [ "$OUTPUT_FORMAT" = "json" ] && [ -f "test-report.json" ]; then
        print_status "JSON report generated: test-report.json"
    fi
    
    if [ "$OUTPUT_FORMAT" = "html" ] && [ -f "test-report.html" ]; then
        print_status "HTML report generated: test-report.html"
    fi
}

# Main execution
main() {
    print_status "Starting test runner..."
    print_status "Container environment: $(is_container && echo 'Yes' || echo 'No')"
    
    # Install dependencies
    install_dependencies
    
    # Check environment variables
    check_environment
    
    # Wait for service if needed
    wait_for_service
    
    # Run tests
    if run_tests; then
        generate_summary
        print_success "All tests completed successfully!"
        exit 0
    else
        print_error "Tests failed!"
        exit 1
    fi
}

# Run main function
main "$@" 