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

You can download mimic from pypi using pip or easy_install:

``pip install mimc``



Source Code and Issue Tracker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The sourcecode is available on github at 
`https://github.com/gmcquillan/mimic/ <https://github.com/gmcquillan/mimic/>`_.
