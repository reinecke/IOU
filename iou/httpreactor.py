# The MIT License (MIT)
# 
# Copyright (c) 2014 PIX System, LLC. and Eric Reinecke
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from collections import deque
from datetime import datetime
import time
import threading

import requests

from iou import IOU
from iou_reactor_base import IOUTransportError, IOUReactorTask
from iou_reactor_base import PRIORITY_NORMAL, PRIORITY_BACKGROUND, PRIORITY_HIGH

# Defines the number of seconds a runloop should sleep before running again
RUNLOOP_WAIT_DELAY = 0.1

# HTTP Method Constants
PUT = 1
GET = 2
DELETE = 3
POST = 4
HEAD = 5
OPTIONS = 6

_METHOD_NAME_MAP = {
        1:"PUT",
        2:"GET",
        3:"DELETE",
        4:"POST",
        5:"HEAD",
        6:"OPTIONS"
        }

def name_for_method(method):
    return _METHOD_NAME_MAP[method]

class IOUHTTPTransportError(IOUTransportError):
    '''
    Execption to encapsulate HTTP specific error details
    '''
    status_code = None
    task = None


class IOUHTTPReactorTask(IOUReactorTask):
    '''
    Special reactor task used by the http reactor
    '''
    # user manipulated
    request_method = GET
    request_headers = None
    request_data = None
    request_url = None
    request_parameters = None
    
    def __init__(self, url = None, method = GET):
        super(IOUReactorTask, self).__init__()
        self.request_url = url
        self.request_method = method

    def _request_kwargs(self):
        '''
        returns a keyword argument dictionary to be used with the request
        (except for the url)
        '''
        pairs = (("data", self.request_data),
                ("headers", self.request_headers),
                ("params", self.request_parameters))
        kwargs = dict((pair for pair in pairs if pair[1] is not None))

        return kwargs


class IOUHTTPReactor(object):
    header = None
    json = False # When set to true, promise results will be json unpacked

    _http_session = None
    _queues = None
    _worker = None
    _should_stop = None
    _did_stop = None
    _priorities = (PRIORITY_HIGH, PRIORITY_BACKGROUND, PRIORITY_NORMAL)
    _method_dispatch = None

    def __init__(self):
        # Build up a mapping with priority as key and a deque as value
        # the seperate queues will be depleted based on priority
        self._queues = dict((priority, deque()) for
                priority in self._priorities)
        self.header = {}
        self._should_stop = threading.Event()
        self._did_stop = threading.Event()

        # pre-build the session object and method dispatch
        self._http_session = requests.Session()
        self._method_dispatch = {PUT : self._http_session.put,
                GET : self._http_session.get,
                DELETE : self._http_session.delete,
                POST : self._http_session.post,
                HEAD : self._http_session.head,
                OPTIONS : self._http_session.options}

    
    def start(self):
        '''
        starts the reactor up.
        If blocking is true, this method will block until the reactor is
        stopped.
        '''
        # Create a worker if we haven't already
        if self._worker is None or not self._worker.is_alive():
            self._should_stop.clear()
            self._did_stop.clear()
            self._worker = threading.Thread(target=self._run_loop,
                    name = "IOUHTTPReactor request thread")
            self._worker.daemon = True
            self._worker.start()

    def stop(self, blocking=False, timeout=None):
        '''
        Shuts the reactor down
        will block if blocking is True
        if blocking is True, timeout can be set to a number of seconds
        to wait for the reactor to stop before timing out
        '''
        self._should_stop.set()
        if blocking:
            self._did_stop.wait(timeout)
    
    def update_default_headers(self, headers):
        '''
        Updates the standard headers on the session with the provided
        header dictionary.
        Setting the value of a key to None removes that key from the headers
        entirely.
        '''
        self._http_session.headers.update(headers)

    def submit_task(self, task):
        '''
        takes a pix reactor task and adds it to the internal queue
        returns a promise to be fulfilled on completion of task
        '''
        task.time_scheduled = datetime.utcnow()
        promise_name = (name_for_method(task.request_method)+" "+
                task.request_url)
        task.promise = IOU(promise_name)
        priority = task.priority
        self._queues[priority].append(task)

        return task.promise

    def _pop_task(self):
        '''
        Pops the next task to be run from the queues
        returns None if no tasks to run
        '''
        # iterate through the priority queues from high to low until
        # a task is found
        for priority in self._priorities:
            queue = self._queues[priority]
            if not len(queue):
                continue

            return queue.popleft()

        return None

    def _execute_next_task(self):
        '''
        Determines the next task to run and runs it, fulfilling the promise
        when complete.
        
        Returns the task that was run, even if it failed
        If no tasks were found to run, returns None
        '''
        # TODO: we should re-factor so that completions are run from a seperate
        #       thread pool
        task = self._pop_task()
        if task is None:
            return None
        
        task.time_run = datetime.utcnow()
        # get the method
        try:
            method = self._method_dispatch[task.request_method]
        except KeyError:
            msg = "Invalid HTTP method:${task.request_method}".format(task=task)
            e = IOUHTTPTransportError(msg)
            e.task = task
            task.promise.reject(e)
            task.time_completed = datetime.utcnow()
            return task
        
        # run the method
        response = None
        try:
            response = method(task.request_url, **task._request_kwargs())
            response.raise_for_status()
        except Exception, e:
            import traceback;traceback.print_exc()
            #TODO: make exceptions specific
            encapuslated = IOUHTTPTransportError(e.message)
            encapuslated.underlying_exception = e
            encapuslated.response = response
            task.promise.reject(encapuslated)
            task.time_completed = datetime.utcnow()
            return task

        task.time_completed = datetime.utcnow()
        
        # Make good on the promise
        task.promise.fulfill(response)
        
        return task
    
    def _run_loop(self):
        '''
        The runloop that actually processes the requests.
        This is generally run on a seperate thread.
        '''
        while not self._should_stop.is_set():
            task = self._execute_next_task()
            if task is None:
                # TODO: I may attempt to use threading.Event.wait() in
                #       the future instead
                time.sleep(0.1)
        
        self._did_stop.set()


if __name__ == "__main__":
    reactor = IOUHTTPReactor()
    task = IOUHTTPReactorTask('http://apple.com')
    reactor.start()
    
    print "adding task"
    def log_result(result): print result; reactor.stop()
    def log_error(err): print "ERROR:", err; reactor.stop()
    p = reactor.submit_task(task)
    p.add_handlers(log_result, log_error)
    
    print "waiting..."

    p.wait()
    #reactor.run(True)

