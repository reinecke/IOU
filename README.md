IOU
===

Promise-like data encapsulation aimed at asynchronous behavior

Tutorial
--------
Very simply put, IOUs give you a way of describing *what* to do with data while
allowing you to think about *when* the data will be available secondarily. An
IOU is simply a wrapper for a peice of data that will be provided in the future
saying "when we get this data, do these other things."

Here is an example of setting up data dependency with IOUs:
```python
from __future__ import print_function
from iou import IOU

iou1 = IOU()
iou1.add_fulfilled_handler(lambda x:print("original:", x))
plus_seven_iou = iou1.add_fulfilled_handler(lambda x:x+7)

plus_seven_iou.add_fulfilled_handler(lambda x:print("plus seven:", x))

iou1.fulfill(10) # fulfill the original iou with a value of 10
```

The output of this would be:

```
original: 10
plus seven: 17
```

So, what happened here exactly? We created our intial IOU `iou1`. This is a
wrapper for some value that might be provided in the future. We then use
`iou1.add_fulfilled_handler` to say when `iou1` is fulfilled, call the
function provided with the value the IOU was fulfilled with.

We then call `iou.add_fulfilled_handler` with a simple lambda that adds 7 to
whatever value it's called with. In the first call to
`iou1.add_fulfilled_handler` we didn't do anything with the return value.
In the second call though, you'll notice we assign
`plus_seven_iou` with the result of `iou1.add_fulfilled_handler`. Any time
you add a fulfilled handler to an IOU, you receive another IOU that will be 
fulfilled with the result of that handler. So, `plus_seven_iou` represents an
IOU that will be fulfilled with the value of `lambda x:x+7` when called with
the value of `iou1`.

Next, we add a print handler to `plus_seven_iou to` print it's value.

Finally, we fulfill the original IOU, `iou1` with the value `10`. By doing this,
we cause the entire chain of IOUs to evaluate.

That was one of the simpler examples. But let's imagine you have code that looks
something like:
```python
value = compute_large_value()

other_value1 = grab_other_value(value)
other_value2 = grab_another_value(value)

print("Final values are:", other_value1, other_value2)
```

This is pretty simple to do synchronously. The problem is that you are waiting
for both `other_value1` and `other_value2` to be gotten in order. What if there
was a way to execute these things as much in parallel as possible?

Enter the IOU:

```python
# IOU-Aware versions of the other fuctions are used
value_iou = iou_for_computed_large_value()

other_iou1 = value_iou.add_fulfilled_handler(grab_other_value)
other_iou2 = value_iou.add_fulfilled_handler(grab_another_value)

# Wait for both the IOUs to be fulfilled before printing their values
other_iou1.wait()
other_iou2.wait()
print("Final values are:", other_iou1.value, other_iou2.value)
```

Just like IOUs can be *fulfilled*, they can also be *rejected*. That is to say,
if there is an error in generating the value to fulfill the IOU with, it will be
rejected with the appropriate exception. When this happens, none of the
fulfilled handlers will be be called, instead the rejected handlers will be
called with the exception. Also, the value of the IOU will be set to the
exception as well. Rejection handlers can be added similarly to fulfilled
handlers, but using `add_rejected_handler` instead. This method also returns an
IOU to be fulfilled with the result of the rejected handler.

There is much more to the implementation of the IOUs, I hope to document this
in the near future.

httpreactor
-----------
The httpreactor module within the IOU package provides a proof-of-concept
implementation of an API that provides an asynchronous wrapper around the
requests module that is IOU aware.

Here is an example of how to use it to fetch http://www.python.org:

```python
from IOU import httpreactor

# create the reactor to handle HTTP requests and start it up
reactor = httpreactor.IOUHTTPReactor()
reactor.start()

# create a request and submit it to the reactor
request = httpreactor.IOUHTTPReactorTask('http://www.python.org')
request_result_iou = reactor.submit_task(request)

# When the request completes, log the HTTP status code
request_result_iou.add_fulfilled_handler(lambda x:print(x.status_code))
```

Note that none of the calls are blocking :)

Project Status
--------------
Currently at proof-of-concept stage. The main TODOs are:
- Finish out documentation
- Create an IOU that joins to other IOUs?
- Clarify threaded behavior

To expand more, it could be interesting to have the IOU system able to execute
fulfillment/rejection handlers using a thread pool. This way the system could
have a mechanisim to somewhat auto-parallelize.

Acknowledgements
----------------
The design of the IOU system was largely influenced by Keith Rarick's blog
post [Asynchronous Programming in Python](http://xph.us/2009/12/10/asynchronous-programming-in-python.html).

Thanks also to [PIX System, LLC.](http://www.pixsystem.com) for encouraging me
to chase this effort on company time and supporting sharing to the open source
ecosystem.
