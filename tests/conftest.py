import pytest
import logging

from src.config.log_config import setup_logging


@pytest.fixture(scope="session", autouse=True)
def initialize_tests():
    """
    全局初始化 fixture
    scope="session": 整个测试会话只执行一次，避免每个用例都重复配置日志
    autouse=True: 自动应用到所有测试，无需手动在每个测试函数中引用
    """
    # 强制指定环境为 'testing'，确保输出到控制台
    setup_logging(
        app_env="testing",
        log_level="DEBUG",
        service_name="test_runner"
    )

    # 可以在这里打印一句，确认加载成功
    logging.info("🚧 Testing environment initialized. Logging setup complete.")