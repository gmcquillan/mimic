======
Mimic
======

Mimic is an open source mock object framework for Python based on Mox, inspired by
the Java library EasyMock.

Installation
^^^^^^^^^^^^

.. sourcecode:: bash

  $ python setup.py install

To run Mimic's internal tests:

.. sourcecode:: bash

  $ python mimic_test.py

Basic Usage
^^^^^^^^^^^

.. sourcecode:: python

  import unittest
  import mimic

  class PersonTest(mimic.MimicTestBase):

    def testUsingMimic(self):
      # Create a mock Person
      mock_person = self.mimic.CreateMock(Person)

      test_person = ...
      test_primary_key = ...
      unknown_person = ...

      # Expect InsertPerson to be called with test_person; return
      # test_primary_key at that point
      mock_person.InsertPerson(test_person).AndReturn(test_primary_key)

      # Raise an exception when this is called
      mock_person.DeletePerson(unknown_person).AndRaise(UnknownPersonError())

      # Switch from record mode to replay mode
      self.mimic.ReplayAll()

      # Run the test
      ret_pk = mock_person.InsertPerson(test_person)
      self.assertEquals(test_primary_key, ret_pk)
      self.assertRaises(UnknownPersonError, mock_person, unknown_person)


Documentation and Links
^^^^^^^^^^^^^^^^^^^^^^^

For more documentation, see:

    https://mimic.readthedocs.org/en/latest/

For more information, see:

    https://github.com/gmcquillan/mimic

To see information about the project that Mimic is forked from, see:

    http://code.google.com/p/pymox/

The Mox user and developer discussion group is:

  http://groups.google.com/group/mox-discuss

Mox/Mimic is Copyright 2008 Google Inc, and licensed under the Apache
License, Version 2.0; see the file COPYING for details.  If you would
like to help us improve Mox/Mimic, join the group.
