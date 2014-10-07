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
handler function provided with the value the IOU was fulfilled with.

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

Another way to put it would be like this:

1. create `iou1`
2. make a handler that will print the value `iou1` id fulfilled with
3. make an IOU (`plus_seven_iou`) that will be fulfilled with the value of `iou1` plus 7
4. make a handler that will print the value `plus_seven_iou` is fulfilled with
5. fulfill `iou1` with a value of `10`, causing the chain of fulfilled handlers to get executed

That was maybe a less useful example. But let's imagine you have code that looks
something like:
```python
# Fetch the person object from the server for "ereinecke"
person = person_from_server("ereinecke")

# Push the first and last name for person to UI fields
first_name_text_field.set_text(person.first_name)
last_name_text_field.set_text(person.last_name)
```

If `person_from_server` takes some amount of time, you could end up blocking
your UI until you get the result.

What if you made a version of your sever client that made requests on another
thread and then fulfilled IOUs for the requests on the main thread:

```python
# IOU-Aware variant of person_from_server
person_iou = iou_for_person_from_server("ereinecke")

# Tell the IOU to set the text fields on completion
person_iou.add_fulfilled_handler(
    lambda p:first_name_text_field.set_text(p.first_name))
person_iou.add_fulfilled_handler(
    lambda p:last_name_text_field.set_text(p.last_name))
```

This allows for the implementation of non-blocking APIs fairly simply. See the
`iou.httpreactor` sub-module for an example of a non-blocking http request API!

### Rejection
Just like IOUs can be *fulfilled*, they can also be *rejected*. That is to say,
if there is an error in generating the value to fulfill the IOU with, it will be
rejected with the appropriate exception. When this happens, none of the
fulfilled handlers will be be called, instead the rejected handlers will be
called with the exception. Also, the value of the IOU will be set to the
exception as well. Rejection handlers can be added similarly to fulfilled
handlers, but using `add_rejected_handler` instead. This method also returns an
IOU to be fulfilled with the result of the rejected handler.

### Chaining
There is one special cases in which you'll be given `None` when using 
`add_fulfilled_handler`. This is when the handler is another IOU. In 
this case, the handler IOU is *chained* to the IOU you added it to.
This means that the chained IOU will be settled with the same result
as the IOU it's a handler for.

Here is an example:

```
from __future__ import print_function
from iou import IOU
iou1 = IOU()
iou2 = IOU()
iou2.add_fulfilled_handler(print)
iou2.add_rejected_handler(lambda e:print("exception:", e))
iou1.add_fulfilled_handler(iou2)
iou1.reject(Exception("bad stuff happened"))
```

When this is run, the output would be:

`exception: bad stuff happened`

Another place where chaining happens is if the handler's *result* is an IOU, when
this happens, the IOU you were given when you registered the handler is chained
to the resultant IOU. This is to day, the IOU that was returned by the handler
will also fulfill the IOU you got when you registered the handler. This 
facilitates the `then()` behavior of other promise systems.

Here is a theorretical example:
```python
con = MyConnectionToServer('database.mycompany.com')
login_iou = con.login('username', 'password')  # returns an IOU to a session object

# We don't actually use the session object, but want to wait until the connection
# is established before calling user_for_username
user_iou = connection_iou.add_fulfilled_handler(
        lambda _:con.user_for_username('ereinecke'))

# Log the name of the user and delete him
user_iou.add_fulfilled_handler(lambda user:print("I am deleting:", user.name))
user_delete_iou = user_iou.add_fulfilled_handler(lambda user:user.delete())

# once the deletion is complete, logout
user_delete_iou.add_fulfilled_handler(lambda _:con.logout())
```

What happens when you add an IOU as a rejected handler? Weird stuff. I'm open
to ideas about what to do here, [let me know!](https://github.com/reinecke/IOU/issues/new)

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
