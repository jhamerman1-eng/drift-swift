import inspect
from bots.hedge.main import run

def test_run_is_coroutine():
    assert inspect.iscoroutinefunction(run)
