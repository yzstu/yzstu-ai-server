import datetime
import json
import logging
import logging.handlers
import os
import sys

from src.config.constant import Environment
from src.config.settings import get_settings


# ----------------------------------------------------------------------
# 1. 自定义 JSON Formatter (用于生产环境)
# ----------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    """
    企业级 JSON 格式化器
    将日志记录转换为 JSON 字符串，包含时间戳、级别、消息、异常信息等。
    """

    def format(self, record: logging.LogRecord) -> str:
        # 基础字段
        log_record = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }

        # 如果有 extra 字段 (logger.info("msg", extra={'user_id': 123}))
        # 将其合并到顶层或放入 extra 字段中
        if hasattr(record, 'extra_data'):
            log_record.update(record.extra_data)

        # 处理异常信息 (Traceback)
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            # 也可以选择结构化异常堆栈
            # log_record["stack_trace"] = traceback.format_exception(*record.exc_info)

        return json.dumps(log_record, ensure_ascii=False)


# ----------------------------------------------------------------------
# 2. 主配置函数
# ----------------------------------------------------------------------
def setup_logging(
        app_env: str = Environment.DEVELOPMENT.value,
        log_dir: str = get_settings().logger.dir,
        service_name: str = get_settings().app_name,
        log_level: str = get_settings().logger.level
) -> None:
    """
    配置全局日志
    :param app_env: 运行环境 'development', 'testing', 'production'
    :param log_dir: 日志文件存放目录 (仅生产环境有效)
    :param service_name: 日志文件名及服务标识
    :param log_level: 日志级别
    """

    # 获取根 Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # 清空已有的 handlers (防止重复日志)
    root_logger.handlers = []

    # 定义格式
    # 开发/测试环境：人类可读格式
    dev_formatter = logging.Formatter(
        fmt='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # 生产环境：机器可读 JSON 格式
    prod_formatter = JSONFormatter()

    # ----------------------------------------------------
    # 场景 A: Development / Testing -> 控制台 (Stdout)
    # ----------------------------------------------------
    if app_env.lower() in ["development", "testing"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(dev_formatter)
        root_logger.addHandler(console_handler)

        # 可选：在开发环境打印一条提示
        print(f"✅ Logging initialized for {app_env}: Output to Console")

    # ----------------------------------------------------
    # 场景 B: Production -> 文件 (File + Rotation)
    # ----------------------------------------------------
    elif app_env.lower() == "production":
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file_path = os.path.join(log_dir, f"{service_name}.log")

        # 使用 RotatingFileHandler (按大小切割)
        # maxBytes=10MB, backupCount=5 (保留5个备份)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(prod_formatter)
        root_logger.addHandler(file_handler)

        # 生产环境通常也建议保留一个输出到 stderr 的 handler，
        # 用于捕捉 Docker/K8s 容器崩溃前的最后呐喊，或者配合 fluentd 采集容器标准输出
        # 如果你只想要文件，可以注释掉下面这几行
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(prod_formatter)
        root_logger.addHandler(console_handler)

    else:
        # 默认回退到控制台
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(dev_formatter)
        root_logger.addHandler(console_handler)
        logging.warning(f"Unknown environment '{app_env}', defaulting to console logging.")

    # ----------------------------------------------------
    # 3. 屏蔽第三方库的嘈杂日志 (Enterprise Standard)
    # ----------------------------------------------------
    # 很多库 (如 boto3, urllib3) DEBUG 级别废话太多，强制设为 WARNING
    noisy_libraries = ["urllib3", "boto3", "botocore", "requests"]
    for lib in noisy_libraries:
        logging.getLogger(lib).setLevel(logging.WARNING)