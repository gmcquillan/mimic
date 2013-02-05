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
    The pymox project also has 
    `very decent documentation <https://code.google.com/p/pymox/wiki/MoxDocumentation>`_

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

Often this will happen in a test classes ``SetUp`` function. But! you can save
yourself the trouble by having your test class inherit from ``mimic.MimccTestBase``!

When you do this, you get a ``self.mimic`` instance for free. However, that's
not the only reason to do so. The other advantage is that the "Unsetting stubs"
step will be done automatically at the end of each test_functon (more on this later);
together this step saves a lot of boiler plate.

Mocking Out Objects
^^^^^^^^^^^^^^^^^^^


Replaying Mock Objects
^^^^^^^^^^^^^^^^^^^^^^


Unsetting Stubs
^^^^^^^^^^^^^^^
