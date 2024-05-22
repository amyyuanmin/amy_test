"""
*****************************************************************************
Copyright (c) 2018 Marvell International Ltd. and its affiliates.
All rights reserved.
*
If you received this File from Marvell and you have entered into a commercial
license agreement (a "Commercial License") with Marvell, the File is licensed
to you under the terms of the applicable Commercial License.
******************************************************************************
"""


from functools import wraps
from operator import eq, lt, ne, gt
from time import sleep
from ex_thread import run_with_timeout
from threading import Event
import logging
from multiprocessing import TimeoutError
logger = logging.getLogger(__name__)


def wait_for_return_value(
        function_getter, required_value,
        attempts=10, time_sleep=5, compare_operator='equal'):
    """Run the specified function and expect it to return the
    given return value.

    Args:
        function_getter (func): Callable object without parameters.
        required_value :         Expected value from 'function_getter'.
        attempts (str):         Attempts number.
        time_sleep (str):       Time to wait before the next attempt.
        compare_operator (str): Operator to compare a real
            return value and the required value. Possible values:
            more than | less than | equal | different

    Examples:
        function_getter = functools.partial(os.path.exists, r"D:\temp")
        wait_for_return_value(function_getter, True)
    """
    attempts = int(attempts)
    time_sleep = int(time_sleep)
    operator = {
        "more than": gt,
        "less than": lt,
        "equal": eq,
        "different": ne
    }
    while attempts > 0:
        got_value = function_getter()
        logger.debug("Condition: {0} {1} {2} ".format(got_value, compare_operator, required_value))
        if operator[compare_operator](
                got_value, required_value):
            logger.debug("Condition return True...Exit")
            return
        attempts -= 1
        logger.debug("Condition return False")
        logger.debug("{0} attempts left. Wait for {1}".format(attempts, time_sleep))
        sleep(time_sleep)

    raise AssertionError(
        "There are no attempts left for waiting")


def waiter_wrapper(top_attempts=150,
                   sleep_time=2,
                   exception_types=(AssertionError,),
                   action_on_fail=None):
    """A function that takes a keyword/function with arguments and
    tries to run it until it's finished successfully. It will catch and
    except every exception from 'exception_types'. An exception
    will be raised if the keyword still fails after all attempts.

    Args:
        top_attempts (int):      Attempts number.
        sleep_time (int):        Time to wait before the next attempt.
        exception_types (tuple): Exceptions to catch.
        action_on_fail (func):   Function to run before the next attempt.

    Examples:
        waiter_wrapper(top_attempts, sleep_time)(keyword)(args)
        waiter_wrapper(top_attempts, sleep_time, action_on_fail=some_function)(keyword)(args)
        waiter_wrapper(top_attempts=5, exception_types=(NVMeNotFoundError,))(verify_nvme_devices)()

      If 'some_function' needs to have args, it has to be prepared like:
        functools.partial(some_function, fail_args, )

    Where:
      keyword - A keyword/function to run.
      args - Arguments for the keyword.
    """

    def outer_wrapper(keyword):
        @wraps(keyword)
        def inner_wrapper(*args, **kwargs):
            logger.debug('Running keyword {}'.format(keyword))
            for i in range(int(top_attempts)):
                logger.debug('Attempt #{}'.format(i))
                try:
                    result = keyword(*args, **kwargs)
                    break
                except exception_types as err:
                    logger.debug(
                        'Keyword {0} finished unsuccessfully, '
                        'because of following error: {1}'.format(
                            keyword.__name__, err))
                    if i != int(top_attempts) - 1:
                        logger.debug('Waiting %s seconds...' % sleep_time)
                        sleep(int(sleep_time))

                        if action_on_fail is not None:
                            logger.debug(
                                "Trying action on fail {0)..."
                                .format(action_on_fail))
                            action_on_fail()

                    else:
                        logger.debug(
                            'No attempts left while waiting keyword to be '
                            'finished successfully')
                        raise err
            return result

        return inner_wrapper

    return outer_wrapper


def timeout_decorator(max_timeout=15):
    """Timeout decorator used to limit the execution time of the
    given function. Raises a TimeoutError if execution exceeds
    'max_timeout'.

    Args:
        max_timeout (int): Timeout in seconds.

    Examples:
        >> @timeout_decorator(max_timeout=blocking_timeout)
        >> def _try_to_get_resource(*args):
        >>     pass
    """
    def wrapper(item):
        """Wrap the original function."""
        @wraps(item)
        def func_wrapper(*args, **kwargs):
            """Closure for function."""
            stop_event = Event()
            kwargs["stop_event"] = stop_event
            try:
                return run_with_timeout(item, args=args, kwargs=kwargs, timeout=max_timeout)
            except TimeoutError:
                stop_event.set()
                raise
        return func_wrapper
    return wrapper
