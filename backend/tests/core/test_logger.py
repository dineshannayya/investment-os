from app.core.logger import get_logger


#Test 1 – Logger Creation
def test_get_logger_returns_logger():
    logger = get_logger(__name__)

    assert logger is not None

#Test 2 – Logger Name
def test_logger_name():
    logger = get_logger("investment")

    assert logger.name == "investment"

#Test 3 – Singleton Behavior
def test_same_logger_instance():
    logger1 = get_logger("investment")
    logger2 = get_logger("investment")

    assert logger1 is logger2


# Test 4 – Different Names
def test_different_loggers():
    logger1 = get_logger("app.main")
    logger2 = get_logger("app.db")

    assert logger1 is not logger2
