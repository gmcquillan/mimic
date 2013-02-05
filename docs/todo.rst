====
TODO
====

Things that need doing for the project to flourish.

High-level Projects
-------------------

- Full Python3 support, preferably with backwards compatibility to 2.7.
  There is ongoing work on the ``python3`` branch in this repo. If you currently
  work in python3 and would like to use pymox or mimic, please take a look.

    - Current status for the ``python3`` branch is *72* failing tests out of 230.
      But basic mocking and replay of mock objects does seem to work.
    - The ``python3`` branch relies on the `six <http://packages.python.org/six/>`_ module.


Low-hanging Fruit
-----------------

- Convert all of Mimic and Mimic tests to be PEP8 compatible.
- Use RST docstrings to give use autodoc capabilities with Sphinx
