from enum import Enum
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"