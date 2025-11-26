# logger_setup.py
import logging

def setup_logging(level=logging.DEBUG):
    # 自定义输出格式 调用日志的程序函数名 + 当前时间
    fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=level,
                        format=fmt,
                        datefmt="%Y-%m-%d %H:%M:%S")
    # optionally tune mitmproxy/requests libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)

if __name__ == '__main__':
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("程序启动成功")
    logger.debug("进行Debug")
    logger.warning("程序出现问题，但不会报错")
    logger.error("操作失败")
