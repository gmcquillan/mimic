==============
Mimic Tutorial
==============

There are a few core concepts to understand about how Mimic works. Essentially,
there's the part of the test where you setup your expectations, and then there's
the part where you put your mocks into replay mode and call your code like normal.

.. warning::
    Be careful when stubbing out your dependencies, mimic enfoces the contract you setup
    with it. If you say something gets called and it doesn't, mimic will raise an
    exception. You must provide a precise, deterministic view into what these Mock
    objects would do in regular service.


.. note::
    The pymox project also has `decent documentation`_.

.. _decent documentation: https://code.google.com/p/pymox/wiki/MoxDocumentation

Basics
------

Here's a rundown of the stages of a mimic-based test:

- Mimic instance
- Mocking out objects
- Replaying the mock objects
- Verifying and Unsetting the stubs (or ending Replay mode)

Mimic Instance
^^^^^^^^^^^^^^

One way or another, you need a mimic instance from which to issue your commands
for which class, methods, or other structures need to be made into mock objects.

In many examples, you might see a situation like this:

.. sourcecode:: python

    from mimic import Mimic
    mime = Mimic()

Often this will happen in a test classes ``setUp`` method. However, you can save
yourself the trouble by having your test class inherit from ``mimic.MimicTestBase``:

When you do this, you get a ``self.mimic`` instance for free. However, that's
not the only reason to do so. The other advantage is that the "Unsetting stubs"
step will be done automatically at the end of each test method
(:ref:`more on this later <unsetting-stubs-verification>`).

.. sourcecode:: python

   class MyTests(mimc.MimicTestBase):

       def test_something(self):
           self.mimic.stub_out_with_mock(...)


Mocking Out Objects
^^^^^^^^^^^^^^^^^^^

Mocking Out A Function Call
"""""""""""""""""""""""""""

A vast majority of mocking can just be done by calling ``stub_out_with_mock``,
this is good for situations in which you just need to override a particular
function call so it doesn't interact with an external system (database), and/or
you need to control the return values that the function returns.

.. sourcecode:: python

    # Now assuming that your test classes inherit from MimicTestBase
    self.mimic.stub_out_with_mock(my_module, 'my_func')
    my_module.my_func(mimic.ignore_arg()).and_return('Completed')

Mocking Out An Object
"""""""""""""""""""""""

In situations where you need to access attributes and call functions on an object

.. sourcecode:: python

    my_module = self.mimic.create_mock_anything()
    my_module.my_func(mimic.ignore_arg()).and_return('Completed')

Mocking Out A Class
"""""""""""""""""""

In other situations you need to mock out the creation of an instance within the
code that's being tested. In those cases use ``stub_out_class_with_mocks``.

See :ref:`stubbing_out_a_class`

Replaying Mock Objects
^^^^^^^^^^^^^^^^^^^^^^

After setting expectations, we trigger ``replay mode`` which means that we can
make our calls for testing now.

.. sourcecode:: python

    # Set expectations
    self.mimic.replay_all()

    # Call your code
    # Make your assertions
    self.assertTrue(my_func())

.. _unsetting-stubs-verification:

Unsetting Stubs/Verification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After all the mocks have played out (successfully hopefully!) we need to let Mimic
know that it's time to count all the calls and arguments that we setup in our 
expectations.

.. sourcecode:: python

    self.mimic.verify_all()

.. note:: This isn't necessary if you're inheriting from ``mimic.MimicTestBase``!
    self.mimic.verify_all() will be called for you in that case!

