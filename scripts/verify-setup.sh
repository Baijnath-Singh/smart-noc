#!/bin/bash
# Smart NOC - Verification Script for WSL/Linux

echo "🔍 Smart NOC - Environment Verification"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check command
check_command() {
    local cmd=$1
    local name=$2
    local version_cmd=$3
    
    echo -n "Checking $name: "
    if command -v $cmd &> /dev/null; then
        if [ -n "$version_cmd" ]; then
            version=$($version_cmd 2>&1 | head -n1)
            echo -e "${GREEN}✅ $version${NC}"
        else
            echo -e "${GREEN}✅ Installed${NC}"
        fi
        return 0
    else
        echo -e "${RED}❌ Not found${NC}"
        return 1
    fi
}

# Check essential tools
check_command "docker" "Docker" "docker --version"
check_command "docker" "Docker Compose" "docker compose version"
check_command "python3" "Python" "python3 --version"
check_command "go" "Go" "go version"
check_command "git" "Git" "git --version"
check_command "curl" "curl" "curl --version | head -n1"

echo ""
echo "🔍 Checking Docker daemon..."
if docker ps &> /dev/null; then
    echo -e "${GREEN}✅ Docker daemon running${NC}"
else
    echo -e "${RED}❌ Docker daemon not accessible${NC}"
    echo -e "${YELLOW}Tip: Check Docker Desktop is running on Windows${NC}"
fi

echo ""
echo "🔍 Checking project structure..."
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✅ docker-compose.yml found${NC}"
else
    echo -e "${RED}❌ docker-compose.yml not found${NC}"
    echo -e "${YELLOW}Are you in the project root directory?${NC}"
fi

if [ -f "README.md" ]; then
    echo -e "${GREEN}✅ README.md found${NC}"
else
    echo -e "${RED}❌ README.md not found${NC}"
fi

echo ""
echo "🔍 Checking system resources..."
total_mem=$(free -g | awk '/^Mem:/{print $2}')
echo "Total Memory: ${total_mem}GB"
if [ $total_mem -ge 8 ]; then
    echo -e "${GREEN}✅ Sufficient memory${NC}"
else
    echo -e "${YELLOW}⚠️  Less than 8GB RAM - may struggle with full system${NC}"
fi

disk_free=$(df -h . | awk 'NR==2 {print $4}')
echo "Free Disk Space: $disk_free"

echo ""
echo "📊 Summary"
echo "=========="
echo "If all checks show ✅, you're ready to proceed!"
echo ""
echo "Next steps:"
echo "1. Review: README.md"
echo "2. Quick start: QUICKSTART.md"
echo "3. Detailed setup: docs/PHASE-0-SETUP.md"
echo ""
echo "To start the system:"
echo "  docker compose up -d"
echo ""
