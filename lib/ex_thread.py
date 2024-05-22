#!/usr/bin/python
'''******************************************************************************
   Copyright (c) 2018 Marvell International Ltd. and its affiliates.
   All rights reserved.
   *
   If you received this File from Marvell and you have entered into a commercial
   license agreement (a "Commercial License") with Marvell, the File is licensed
   to you under the terms of the applicable Commercial License.
   ******************************************************************************'''


import threading
import traceback
import queue
from multiprocessing import TimeoutError
import logging

logger = logging.getLogger("thread")
logger.setLevel("WARNING")


def run_commands_in_thread(commands, args=()):
    """The method provides the ability to run several different commands in separate threads
        and get result list all execution commands.

    Args:
        commands (str | list): list of commands to run
        args: (str | list): list of commands arguments
    Returns:
        out (str | list): list with the results of all commands
    """
    threads = list()
    out = list()
    for command in commands:
        thread = ExThread(target=command, args=args)
        threads.append(thread)
        thread.start()
    for thread in threads:
        result = thread.join()
        out.append(result)
    return out


def get_function_result(thread, timeout):
    """Getting the results of executing the functions launched in the thread,
     or ExceptionThread if the timeout is exceeded.

     Examples:
        threads = []
        for x in range(0, 10):
            threads.append(run_function_in_thread(run_tests, str(x + 1)))
        for thread in threads:
            get_function_result(thread, timeout=10)

    Args:
        thread (str): Thread object with function
        timeout(int): Optional argument, which set the function timeout wait in seconds
    Returns:
        list with the results of all commands
    """
    return thread.join(timeout)


def run_function_in_thread(command, args=(), kwargs=None,):
    """The method provides the ability to run function in a separate thread.
    Args:
        command (function): Callable function
        args (str | list): Function positional arguments list
        kwargs (mapping): Function named arguments list
    Returns:
        Thread object with function
    """
    thread = ExThread(target=command, args=args, kwargs=kwargs)
    thread.start()
    return thread


def run_with_timeout(command, args=(), kwargs=None, timeout=300, raise_on_timeout=True):
    """Starting a function in a separate thread and waiting for it to finish before the timeout expires
        If the parameter raise_on_timeout is not set, when the timeout expires, it will be raised TimeoutError
    Args:
        command (function): Callable function
        args (str | list): Function positional arguments list
        kwargs (mapping): Function named arguments list
        timeout(int): Optional argument, which set the function timeout wait in seconds. Default=300 seconds
        raise_on_timeout(boolean):

    Returns:
        if the function is completed before the timeout expires, its result will be returned, otherwise -
        will be raised TimeoutError
    """
    thread_join = None
    thread = ExThread(target=command, args=args, kwargs=kwargs)
    thread.start()
    try:
        thread_join = thread.join(timeout)
    except TimeoutError as e:
        if raise_on_timeout:
            raise e
    return thread_join


class ExThread(threading.Thread):
    """A class that represents a Extended thread of control with custom Exception handles.
       """
    def __init__(
            self, group=None, target=None, name=None,
            args=(), kwargs=None):
        """
            This constructor should always be called with keyword arguments
        Args:
            group (): Should be None; reserved for future extension when a ThreadGroup
                    class is implemented.
            target (): Callable object to be invoked by the run()
                    method. Defaults to None, meaning nothing is called
            name (str): Thread name. By default, a unique name is constructed of
                    the form "Thread-N" where N is a small decimal number
            args (tuple): Argument tuple for the target invocation
            kwargs (dict): A dictionary of keyword arguments for the target
                    invocation
        """

        threading.Thread.__init__(
            self, group=group, target=target, name=name, args=args, kwargs=kwargs)
        self.__status_queue = queue.Queue()
        self.target = target
        self.result = None
        self.args = args
        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs
        self.daemon = True

    def run(self):
        """This method should NOT be overriden.
            Method representing the thread's activity.
        """
        logger.debug(
            'Starting {0} {1}({2}, {3})'.format(
                self.name, self.target, self.args, self.kwargs))

        try:
            self.result = self.target(*self.args, **self.kwargs)
            self.__status_queue.put((None, None))
        except Exception as e:
            e_traceback = traceback.format_exc()
            self.__status_queue.put((e, e_traceback))

    def wait_for_exc_info(self):
        """Remove and return an item from the threads queue.
        """
        return self.__status_queue.get()

    def join_with_exception(self):
        """Remove and return an item from the threads queue. If an error occurred and  error trace exist,
            will be raised Exception with trace
        """
        e, trace = self.wait_for_exc_info()
        if e is None:
            logger.debug('Got %s from %s %s' % (
                self.result, self.name, self.target))
        else:
            logger.error(trace)
            raise e

    def join(self, timeout=None):
        """Wait until the thread terminates.

                This blocks the calling thread until the thread whose join() method is
                called terminates -- either normally or through an unhandled exception
                or until the optional timeout occurs.

                When the timeout argument is present and not None, it should be a
                floating point number specifying a timeout for the operation in seconds
                (or fractions thereof). As join() always returns None, you must call
                isAlive() after join() to decide whether a timeout happened -- if the
                thread is still alive, the join() call timed out.

                When the timeout argument is not present or None, the operation will
                block until the thread terminates.
                """
        if timeout is not None:
            logger.debug(
                'Waiting for {0} thread {1} target for {2} seconds...'.format(
                    self.name, self.target, timeout))
        else:
            logger.warning(
                'WARNING: joining {0} thread without timeout'.format(self.name))

        threading.Thread.join(self, timeout)
        if self.is_alive() is True:
            raise TimeoutError(
                'Timeout of {0}s for thread {1} join occurred. '
                'Target: {2}, args: {3}, kwargs: {4}'.format(
                    timeout, self.name, self.target,
                    self.args, self.kwargs))
        self.join_with_exception()
        return self.result
