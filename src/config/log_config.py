import logging
import logging.config
from pathlib import Path

from .constant import PROJECT_ROOT


def setup_logging(config_path=f'{PROJECT_ROOT}/logging.yaml'):
    """根据YAML配置文件初始化日志"""
    if Path(config_path).exists():
        with open(config_path, 'r') as f:
            import yaml
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)
    else:
        # 提供一个基础的回退配置
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),  # 输出到控制台
                logging.FileHandler('app.log')  # 输出到文件
            ]
        )