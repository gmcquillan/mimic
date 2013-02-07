========
Advanced
========


Variable Parameters to Mock Functions
-------------------------------------


IgnoreArg()
^^^^^^^^^^^^^^^^^


And()
^^^^^^^^^^^


Or()
^^^^^^^^^^


Is()
^^^^^^^^^^


IsA()
^^^^^^^^^^^


IsAlmost()
^^^^^^^^^^^^^^^^


StringContains()
^^^^^^^^^^^^^^^^^^^^^^


Regex()
^^^^^^^^^^^^^


In()
^^^^^^^^^^


Not()
^^^^^^^^^^^


ContainsKeyValue()
^^^^^^^^^^^^^^^^^^^^^^^^


ContainsAttributeValue()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


SameElementAs()
^^^^^^^^^^^^^^^^^^^^^


Calling Mock Objects Multiple Times
-----------------------------------

Mimic is pretty strict about which functions are called, and how many times they're
called. This could be tedious if the same function is called with the same Parameters
and you were required to setup those expectations repeatedly. 

In a situation in which the function ``my_call`` is called three times during the
course of a test, you could do this: 

.. sourcecode:: python

    my_object.my_call().and_return(True)
    my_object.my_call().and_return(True)
    my_object.my_call().and_return(True)

However, you can chain a ``multiple_times()`` call into the first call.

.. sourcecode:: python

    my_object.my_call().multiple_times().and_return(True)
    # Done! :)

Now, if you wanted to make sure it got called three times and no more or no less:

.. sourcecode:: python

    my_object.my_call().multiple_times(3).and_return(True)

.. _stubbing_out_a_class:

Stubbing Out A Class
--------------------

If you need to make an instance with the characteristic of a particular class,
and whose instance attributes and methods you wish to be able to control, try
``stub_out_class_with_mocks``. This is particularly useful when an object is 
instanstiated within the code tested by your test.


.. sourcecode:: python

    self.mimic.stub_out_class_with_mocks(my_module, 'MyClass')
    mock_object = my_module.MyClass()
    # Setup any expectations you want for MyClass


Now you have an object that you can set any expectations you need to override
for your testing.


MockAnything Objects
--------------------

These are sort of like a mock object created by ``stub_out_class_with_mocks``
however, you don't even need to specify a class. It's an empty vessel with which
any expectations you want. This is useful whenever you might need an object, but 
the code you're testing isn't responsible for its creation (e.g. you can pass it
into the function). 

.. sourcecode:: python

    fake_result = self.mimic.create_mock_anything()
    fake_result.result = 'Some fake result data'
    fake_connection = self.mimic.create_mock_anything()
    fake_connection.query(mimic.ignore_arg()).and_return(fake_result)


Stubbing Out Python Builtins
----------------------------

For example, if you need to mock out a python builtin such as ``open``, the 
following code would work:

.. sourcecode:: python

    # Assuming you've setup your mimic instance as self.mimic
    fake_conf_file = StringIO.StringIO('')
    self.mimic.stub_out_with_mock(sys.modules['__builtin__'], 'open')
    sys.modules['__builtin__'].open('path/to/file.txt', 'r').and_return(
        fake_conf_file
    )

    self.mimic.replay_all()

    # Calls you would need to make that interact with filesystems, etc.
