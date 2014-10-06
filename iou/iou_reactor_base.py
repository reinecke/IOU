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

# Reactor task priorities
PRIORITY_BACKGROUND = 90
PRIORITY_NORMAL = 50
PRIORITY_HIGH = 10

class IOUTransportError(Exception):
    '''
    Base exception for errors with the transport mechanisim. In general, 
    specific transports will subclass this with a version that has attributes
    specific to that transport (HTTP transport might subclass with a version
    including the status code, for example)
    '''


class IOUReactorTask(object):
    '''
    Encapsulates a single task to be run by the reactor
    '''
    priority = PRIORITY_NORMAL
    
    # used by reactor
    promise = None
    time_scheduled = None
    time_run = None
    time_completed = None
