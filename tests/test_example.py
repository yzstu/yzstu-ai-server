# test_example.py
import logging

logger = logging.getLogger(__name__)

def test_something():
    logger.info("Running test_something...")
    assert 1 + 1 == 2
    logger.debug("Calculation verified.")

def test_error_handling():
    try:
        1 / 0
    except ZeroDivisionError:
        logger.error("Caught expected division error", exc_info=True)