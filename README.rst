IOU
===

Promise-like data encapsulation aimed at asynchronous behavior

Tutorial
--------

Very simply put, IOUs give you a way of describing *what* to do with
data while allowing you to think about *when* the data will be available
secondarily. An IOU is simply a wrapper for a peice of data that will be
provided in the future saying “when we get this data, do these other
things.”

Here is an example of setting up data dependency with IOUs:

.. code:: python

    from __future__ import print_function
    from iou import IOU

    iou1 = IOU()
    iou1.add_fulfilled_handler(lambda x:print("original:", x))
    plus_seven_iou = iou1.add_fulfilled_handler(lambda x:x+7)

    plus_seven_iou.add_fulfilled_handler(lambda x:print("plus seven:", x))

    iou1.fulfill(10) # fulfill the original iou with a value of 10

The output of this would be:

::

    original: 10
    plus seven: 17

So, what happened here exactly? We created our intial IOU ``iou1``. This
is a wrapper for some value that might be provided in the future. We
then use ``iou1.add_fulfilled_handler`` to say when ``iou1`` is
fulfilled, call the handler function provided with the value the IOU was
fulfilled with.

We then call ``iou.add_fulfilled_handler`` with a simple lambda that
adds 7 to whatever value it’s called with. In the first call to
``iou1.add_fulfilled_handler`` we didn’t do anything with the return
value. In the second call though, you’ll notice we assign
``plus_seven_iou`` with the result of ``iou1.add_fulfilled_handler``.
Any time you add a fulfilled handler to an IOU, you receive another IOU
that will be fulfilled with the result of that handler. So,
``plus_seven_iou`` represents an IOU that will be fulfilled with the
value of ``lambda x:x+7`` when called with the value of ``iou1``.

Next, we add a print handler to ``plus_seven_iou to`` print it’s value.

Finally, we fulfill the original IOU, ``iou1`` with the value ``10``. By
doing this, we cause the entire chain of IOUs to evaluate.

Another way to put it would be like this:

1. create ``iou1``
2. make a handler that will print the value ``iou1`` id fulfilled with
3. make an IOU (``plus_seven_iou``) that will be fulfilled with the
   value of ``iou1`` plus 7
4. make a handler that will print the value ``plus_seven_iou`` is
   fulfilled with
5. fulfill ``iou1`` with a value of ``10``, causing the chain of
   fulfilled handlers to get executed

That was maybe a less useful example. But let’s imagine you have code
that looks something like:

.. code:: python

    # Fetch the person object from the server for "ereinecke"
    person = person_from_server("ereinecke")

    # Push the first and last name for person to UI fields
    first_name_text_field.set_text(person.first_name)
    last_name_text_field.set_text(person.last_name)

If ``person_from_server`` takes some amount of time, you could end up
blocking your UI until you get the result.

What if you made a version of your sever client that made requests on
another thread and then fulfilled IOUs for the requests on the main
thread:

\`\`\`python # IOU-Aware variant of person\_from\_server per
