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

import threading
from collections import deque
import sys, traceback

# Set this to True for incredibly verbose IOU resolution output
TRACE = False

_IOU_COUNT = 0

def _LOG(*args):
    if not TRACE:
        return

    print " ".join([str(a) for a in args])

def _resolve(iou, handler, value):
    '''
    Resolves the provided IOU with handler(value). If handler(value) resolves
    to another IOU, then iou is resgistered to be resolved with the result of
    that new IOU
    '''
    # have the handler settle the iou if it's another iou
    if _is_iou(handler):
        '''
        _LOG("chaining", iou, "to", handler)
        handler.add_settled_handler(iou)
        '''
        handler._push_result_to(iou)

        return
    
    # if the handler isn't a callable, resolve the iou with it
    if not callable(handler):
        _LOG("handler", handler, "treated as constant for", iou)
        iou.fulfill(handler)
        return
    
    # Get the handler result and resolve the iou
    try:
        _LOG("running", handler, "with value", value)
        result = handler(value)

        # chain the original IOU's resolution to the new IOU
        if _is_iou(result):
            _LOG("chaining", iou, "to result", result)
            #result.add_fulfilled_handler(iou.fulfill).name += "-chained"
            # TODO: Need some logic about rejecting chained success IOU on failure
            #result.add_rejected_handler(iou.reject).name += "-chained"
            result._chained_IOUs.append(iou)
            return
    except Exception, e:
        _LOG("rejecting", iou, "with failure of", handler, "because", e)
        iou.reject(e)
    else:
        _LOG("paying", iou, "with result from", handler, ":", result)
        iou.fulfill(result)

def _is_iou(obj):
    return isinstance(obj, IOU)

class IOU(object):
    is_rejected = None
    value = None
    
    _settled_event = None

    _fulfilled_actors = None
    _rejected_actors = None
    _settled_actors = None
    _chained_IOUs = None

    name = None

    def __init__(self, name = None):
        self._settled_event = threading.Event()
        self._fulfilled_actors = deque()
        self._rejected_actors = deque()
        self._settled_actors = deque()
        self._chained_IOUs = deque()
        
        global _IOU_COUNT
        _IOU_COUNT += 1
        
        if name is None:
            self.name = "#"+str(_IOU_COUNT)
        else:
            self.name = name

        _LOG("created:", str(self))

    def __del__(self):
        _LOG("destroyed:", str(self))

    def __repr__(self):
        if self.name is not None:
            return "<IOU %s at 0x%x>"%(self.name, id(self))
        return "<IOU at 0x%x>"%(id(self))
        
    @property
    def is_settled(self):
        '''Returns whether the IOU has been resolved or not

        is_settled will be True if the IOU has been either rejected or
        fulfilled, otherwise it will be False.
        '''
        return self._settled_event and self._settled_event.is_set()
    
    @property
    def is_fulfilled(self):
        '''Returns whether the IOU is fulfilled or not
        '''
        if self.is_settled:
            return not self.is_rejected
        
        # Return None instead of true/false in the event of a pending IOU
        return None
    
    def _resolve_actors(self, actor_deque, value):
        '''Handle the actual resolution of a deque of actors
        '''
        _LOG("resolving", actor_deque, "with", value)
        while actor_deque:
            handler, iou = actor_deque.popleft()
            if _is_iou(handler):
                if self.is_rejected:
                    handler.reject(value)
                    iou.reject(value)
                else:
                    handler.fulfill(value)
                    iou.fulfill(value)
            else:
                _resolve(iou, handler, value)

    def _push_result_to(self, other_iou):
        '''Calls either fulfill or reject on other_iou according to this iou
        '''
        if self.is_rejected:
            other_iou.reject(self.value)
        else:
            other_iou.fulfill(self.value)

    def fulfill(self, value):
        '''Resolve this IOU by fulfilling it

        value is the value the IOU will be fulfilled with
        '''
        if self.is_settled:
            raise ValueError("Cannont re-resolve a promise")
        if value == self:
            raise TypeError("IOU cannot pay itself")

        _LOG("--== fulfilling", self)
        self.value = value
        self.is_rejected = False

        self._resolve_actors(self._fulfilled_actors, value)
        self._resolve_actors(self._settled_actors, value)
        
        # fulfill the chained IOU
        while(self._chained_IOUs):
            chained_iou = self._chained_IOUs.popleft()
            chained_iou.fulfill(value)

        _LOG("--==fulfilled", str(self))
        self._settled_event.set()

    def reject(self, reason):
        '''Resolve this IOU by rejecting it

        reason is the value to reject with (usually an Exception)
        '''
        if reason == self:
            raise TypeError("IOU reject pay itself")
        if self.is_settled:
            raise ValueError("Cannot re-resolve %s with value:%s"%(str(self),
                str(self.value)))
        
        _LOG("--==rejecting", self)
        self.value = reason
        self.is_rejected = True

        self._resolve_actors(self._rejected_actors, reason)
        self._resolve_actors(self._settled_actors, reason)

        for handler, iou in self._fulfilled_actors:
            iou.reject(reason)
        
        # Reject the chained IOU
        while(self._chained_IOUs):
            chained_iou = self._chained_IOUs.popleft()
            chained_iou.reject(reason)

        _LOG("--==rejected", str(self))
        self._settled_event.set()
    
    def add_fulfilled_handler(self, handler):
        '''Adds a handler to be called when the IOU is fulfilled

        The handler will be called with the value the IOU was fulfilled with.

        returns an IOU that will be fulfilled with the result of handler
        '''
        if self == handler:
            raise TypeError("IOU cannot handle itself")
        
        # If the handler is an IOU, use chained behavior
        handler_is_iou = _is_iou(handler)
        if handler_is_iou and self.is_fulfilled:
            handler.fulfill(self.value)
            return
        elif handler_is_iou and self.is_rejected:
            handler.reject(self.value)
            return
        elif handler_is_iou:
            _LOG("chaining", handler, "to", self)
            self._chained_IOUs.append(handler)
            return
        
        out_iou = IOU()
        if self.is_fulfilled:
            _resolve(out_iou, handler, self.value)
        else:
            self._fulfilled_actors.append((handler, out_iou))

        return out_iou

    def add_rejected_handler(self, handler):
        '''Adds a handler to be called when the IOU is rejected

        The handler will be called with the exception that caused the IOU
        to reject.

        returns an IOU that will be fulfilled with the result of handler
        '''
        if self == handler:
            raise TypeError("IOU cannot handle itself")
        
        out_iou = IOU()
        if self.is_rejected:
            _resolve(out_iou, handler, self.value)
        else:
            self._rejected_actors.append((handler, out_iou))

        return out_iou

    def add_handlers(self, fulfilled_handler, rejected_handler):
        '''Adds both a fulfilled and rejected handler in one shot

        returns a tuple (fulfilled_iou, rejected_iou) of ious to be fulfilled
        with their respective handelers return values
        '''
        fulfilled_iou = self.add_fulfilled_handler(fulfilled_handler)
        rejected_iou = self.add_rejected_handler(rejected_handler)

        return (fulfilled_iou, rejected_iou)

    def add_settled_handler(self, handler):
        '''Adds the provided handler to be called when the IOU is resolved
        
        Handler will be called with either the fulfilled value or rejected
        exception, dependent on how this IOU resolves.

        returns an IOU that will be fulfilled with the result of handler
        '''
        if self == handler:
            raise TypeError("IOU cannot handle itself")
        
        out_iou = IOU()
        if self.is_rejected:
            handler.reject(self.value)
        elif self.is_fulfilled:
            handler.fulfill(self.value)
        else:
            self._settled_actors.append((handler, out_iou))

        return out_iou

    def wait(self):
        '''Blocks until the IOU has been resolved
        '''
        if self.is_settled:
            return self.value
        
        # Just wait until the event has been set
        self._settled_event.wait()
        
        return self.value

if __name__ == "__main__":
    import sys
    log = lambda x: sys.stdout.write(str(x)+'\n')
    logerr = lambda e: log("Error:"+str(e))
    
    i = IOU("Base")
    
    i.add_fulfilled_handler(log).name = "log complete"
    i2 = IOU("base2")
    i2.add_fulfilled_handler(lambda x:log("#2:"+str(x)))
    i3 = i.add_fulfilled_handler(i2)
    i3.name = "logging complete"
    
    i.fulfill(6)

    print i3.is_settled

    #i2.fulfill("paid")

