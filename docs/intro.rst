======================
Introduction to Mimic
======================


What is Mimic?
--------------

Mimic is a mock library for python that is based on
`Google's Pymox <https://code.google.com/p/pymox/>`_, a fanstastic testing
library, which is in turn based on EasyMock -- a Java mock object framework.

Mimic allows you to write true unit tests even in situations in which your code is
dependent on external systems, in situations in which dependency injection
won't work, or would otherwise be too complicated.

Mimic Test Philosophy
^^^^^^^^^^^^^^^^^^^^^

Mimic is a bit more complex than many other mocking libraries. This is a strength
and a weakness. The way Mimic tests are meant to be run is in the following order:

- specify expectations
- enter replay mode

So the first part of your test ends up being about setting up the scenario for
mimic, and then the second part -- after you enter replay mode -- is about calling
the code you hope to test from you test function. 

This two-step process is a little extra work from the onset, but it's a hidden
strength when you realize that Mimic holds you to the expectations you set: 
if you don't call a method you mock out, you get an error; if you call a method
you weren't expecting, you get an error. It has a kind of symmetry that many developers
find easy to trust because of its explicitness.

Why fork?
^^^^^^^^^

There are a couple of features that have been needed for a while, including:

- Move the codebase over to github (and thereby git) in order to allow for more community participation
- PEP8 compliant method names
- Experimental Python 3 support
- Complete, comprehensive documentation
- Continuous Integration
- Fixes which have been rejected from pymox proper
    - Nosetests fixes for 'one-character-per-line' exception output

Most importantly, though, a library this good needs active maintenance. It's 
been a few years now since the latest release. While this is a relatively mature
code-base, there are a number of
`outstanding issues <https://code.google.com/p/pymox/issues/list>`_, which don't
seem to be getting any traction. 


Getting Started
---------------

Installing
^^^^^^^^^^

You can download mimic from `PyPI`_ using `pip`_ or easy_install:

.. sourcecode:: bash

   pip install mimic


Source Code and Issue Tracker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The sourcecode is available on github at https://github.com/gmcquillan/mimic/.

.. _PyPI: https://pypi.python.org/
.. _pip: http://www.pip-installer.org/
