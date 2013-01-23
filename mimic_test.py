#!/usr/bin/env python
#
# Unit tests for Mimic.
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cStringIO
import unittest
import re
import sys

import mimic

import mimic_test_helper

OS_LISTDIR = mimic_test_helper.os.listdir

class ExpectedMethodCallsErrorTest(unittest.TestCase):
  """Test creation and string conversion of ExpectedMethodCallsError."""

  def testAtLeastOneMethod(self):
    self.assertRaises(ValueError, mimic.ExpectedMethodCallsError, [])

  def testOneError(self):
    method = mimic.MockMethod("testMethod", [], [], False)
    method(1, 2).AndReturn('output')
    e = mimic.ExpectedMethodCallsError([method])
    self.assertEqual(
        "Verify: Expected methods never called:\n"
        "  0.  testMethod(1, 2) -> 'output'",
        str(e))

  def testManyErrors(self):
    method1 = mimic.MockMethod("testMethod", [], [], False)
    method1(1, 2).AndReturn('output')
    method2 = mimic.MockMethod("testMethod", [], [], False)
    method2(a=1, b=2, c="only named")
    method3 = mimic.MockMethod("testMethod2", [], [], False)
    method3().AndReturn(44)
    method4 = mimic.MockMethod("testMethod", [], [], False)
    method4(1, 2).AndReturn('output')
    e = mimic.ExpectedMethodCallsError([method1, method2, method3, method4])
    self.assertEqual(
        "Verify: Expected methods never called:\n"
        "  0.  testMethod(1, 2) -> 'output'\n"
        "  1.  testMethod(a=1, b=2, c='only named') -> None\n"
        "  2.  testMethod2() -> 44\n"
        "  3.  testMethod(1, 2) -> 'output'",
        str(e))


class OrTest(unittest.TestCase):
  """Test Or correctly chains Comparators."""

  def testValidOr(self):
    """Or should be True if either Comparator returns True."""
    self.assert_(mimic.Or(mimic.IsA(dict), mimic.IsA(str)) == {})
    self.assert_(mimic.Or(mimic.IsA(dict), mimic.IsA(str)) == 'test')
    self.assert_(mimic.Or(mimic.IsA(str), mimic.IsA(str)) == 'test')

  def testInvalidOr(self):
    """Or should be False if both Comparators return False."""
    self.failIf(mimic.Or(mimic.IsA(dict), mimic.IsA(str)) == 0)


class AndTest(unittest.TestCase):
  """Test And correctly chains Comparators."""

  def testValidAnd(self):
    """And should be True if both Comparators return True."""
    self.assert_(mimic.And(mimic.IsA(str), mimic.IsA(str)) == '1')

  def testClauseOneFails(self):
    """And should be False if the first Comparator returns False."""

    self.failIf(mimic.And(mimic.IsA(dict), mimic.IsA(str)) == '1')

  def testAdvancedUsage(self):
    """And should work with other Comparators.

    Note: this test is reliant on In and ContainsKeyValue.
    """
    test_dict = {"mock" : "obj", "testing" : "isCOOL"}
    self.assert_(mimic.And(mimic.In("testing"),
                           mimic.ContainsKeyValue("mock", "obj")) == test_dict)

  def testAdvancedUsageFails(self):
    """Note: this test is reliant on In and ContainsKeyValue."""
    test_dict = {"mock" : "obj", "testing" : "isCOOL"}
    self.failIf(mimic.And(mimic.In("NOTFOUND"),
                          mimic.ContainsKeyValue("mock", "obj")) == test_dict)

class FuncTest(unittest.TestCase):
  """Test Func correctly evaluates based upon true-false return."""

  def testFuncTrueFalseEvaluation(self):
    """Should return True if the validating function returns True."""
    equals_one = lambda x: x == 1
    always_none = lambda x: None

    self.assert_(mimic.Func(equals_one) == 1)
    self.failIf(mimic.Func(equals_one) == 0)


    self.failIf(mimic.Func(always_none) == 1)
    self.failIf(mimic.Func(always_none) == 0)
    self.failIf(mimic.Func(always_none) == None)

  def testFuncExceptionPropagation(self):
    """Exceptions within the validating function should propagate."""
    class TestException(Exception):
      pass

    def raiseExceptionOnNotOne(value):
      if value != 1:
        raise TestException
      else:
        return True

    self.assert_(mimic.Func(raiseExceptionOnNotOne) == 1)
    self.assertRaises(TestException, mimic.Func(raiseExceptionOnNotOne).__eq__, 2)

class SameElementsAsTest(unittest.TestCase):
  """Test SameElementsAs correctly identifies sequences with same elements."""

  def testSortedLists(self):
    """Should return True if two lists are exactly equal."""
    self.assert_(mimic.SameElementsAs([1, 2.0, 'c']) == [1, 2.0, 'c'])

  def testUnsortedLists(self):
    """Should return True if two lists are unequal but have same elements."""
    self.assert_(mimic.SameElementsAs([1, 2.0, 'c']) == [2.0, 'c', 1])

  def testUnhashableLists(self):
    """Should return True if two lists have the same unhashable elements."""
    self.assert_(mimic.SameElementsAs([{'a': 1}, {2: 'b'}]) ==
                 [{2: 'b'}, {'a': 1}])

  def testEmptyLists(self):
    """Should return True for two empty lists."""
    self.assert_(mimic.SameElementsAs([]) == [])

  def testUnequalLists(self):
    """Should return False if the lists are not equal."""
    self.failIf(mimic.SameElementsAs([1, 2.0, 'c']) == [2.0, 'c'])

  def testUnequalUnhashableLists(self):
    """Should return False if two lists with unhashable elements are unequal."""
    self.failIf(mimic.SameElementsAs([{'a': 1}, {2: 'b'}]) == [{2: 'b'}])

  def testActualIsNotASequence(self):
    """Should return False if the actual object is not a sequence."""
    self.failIf(mimic.SameElementsAs([1]) == object())

  def testOneUnhashableObjectInActual(self):
    """Store the entire iterator for a correct comparison.

    In a previous version of SameElementsAs, iteration stopped when an
    unhashable object was encountered and then was restarted, so the actual list
    appeared smaller than it was.
    """
    self.failIf(mimic.SameElementsAs([1, 2]) == iter([{}, 1, 2]))


class ContainsKeyValueTest(unittest.TestCase):
  """Test ContainsKeyValue correctly identifies key/value pairs in a dict.
  """

  def testValidPair(self):
    """Should return True if the key value is in the dict."""
    self.assert_(mimic.ContainsKeyValue("key", 1) == {"key": 1})

  def testInvalidValue(self):
    """Should return False if the value is not correct."""
    self.failIf(mimic.ContainsKeyValue("key", 1) == {"key": 2})

  def testInvalidKey(self):
    """Should return False if they key is not in the dict."""
    self.failIf(mimic.ContainsKeyValue("qux", 1) == {"key": 2})


class ContainsAttributeValueTest(unittest.TestCase):
  """Test ContainsAttributeValue correctly identifies properties in an object.
  """

  def setUp(self):
    """Create an object to test with."""


    class TestObject(object):
      key = 1

    self.test_object = TestObject()

  def testValidPair(self):
    """Should return True if the object has the key attribute and it matches."""
    self.assert_(mimic.ContainsAttributeValue("key", 1) == self.test_object)

  def testInvalidValue(self):
    """Should return False if the value is not correct."""
    self.failIf(mimic.ContainsKeyValue("key", 2) == self.test_object)

  def testInvalidKey(self):
    """Should return False if they the object doesn't have the property."""
    self.failIf(mimic.ContainsKeyValue("qux", 1) == self.test_object)


class InTest(unittest.TestCase):
  """Test In correctly identifies a key in a list/dict"""

  def testItemInList(self):
    """Should return True if the item is in the list."""
    self.assert_(mimic.In(1) == [1, 2, 3])

  def testKeyInDict(self):
    """Should return True if the item is a key in a dict."""
    self.assert_(mimic.In("test") == {"test" : "module"})

  def testItemInTuple(self):
    """Should return True if the item is in the list."""
    self.assert_(mimic.In(1) == (1, 2, 3))

  def testTupleInTupleOfTuples(self):
    self.assert_(mimic.In((1, 2, 3)) == ((1, 2, 3), (1, 2)))

  def testItemNotInList(self):
    self.failIf(mimic.In(1) == [2, 3])

  def testTupleNotInTupleOfTuples(self):
    self.failIf(mimic.In((1, 2)) == ((1, 2, 3), (4, 5)))


class NotTest(unittest.TestCase):
  """Test Not correctly identifies False predicates."""

  def testItemInList(self):
    """Should return True if the item is NOT in the list."""
    self.assert_(mimic.Not(mimic.In(42)) == [1, 2, 3])

  def testKeyInDict(self):
    """Should return True if the item is NOT a key in a dict."""
    self.assert_(mimic.Not(mimic.In("foo")) == {"key" : 42})

  def testInvalidKeyWithNot(self):
    """Should return False if they key is NOT in the dict."""
    self.assert_(mimic.Not(mimic.ContainsKeyValue("qux", 1)) == {"key": 2})


class StrContainsTest(unittest.TestCase):
  """Test StrContains correctly checks for substring occurrence of a parameter.
  """

  def testValidSubstringAtStart(self):
    """Should return True if the substring is at the start of the string."""
    self.assert_(mimic.StrContains("hello") == "hello world")

  def testValidSubstringInMiddle(self):
    """Should return True if the substring is in the middle of the string."""
    self.assert_(mimic.StrContains("lo wo") == "hello world")

  def testValidSubstringAtEnd(self):
    """Should return True if the substring is at the end of the string."""
    self.assert_(mimic.StrContains("ld") == "hello world")

  def testInvaildSubstring(self):
    """Should return False if the substring is not in the string."""
    self.failIf(mimic.StrContains("AAA") == "hello world")

  def testMultipleMatches(self):
    """Should return True if there are multiple occurances of substring."""
    self.assert_(mimic.StrContains("abc") == "ababcabcabcababc")


class RegexTest(unittest.TestCase):
  """Test Regex correctly matches regular expressions."""

  def testIdentifyBadSyntaxDuringInit(self):
    """The user should know immediately if a regex has bad syntax."""
    self.assertRaises(re.error, mimic.Regex, '(a|b')

  def testPatternInMiddle(self):
    """Should return True if the pattern matches at the middle of the string.

    This ensures that re.search is used (instead of re.find).
    """
    self.assert_(mimic.Regex(r"a\s+b") == "x y z a b c")

  def testNonMatchPattern(self):
    """Should return False if the pattern does not match the string."""
    self.failIf(mimic.Regex(r"a\s+b") == "x y z")

  def testFlagsPassedCorrectly(self):
    """Should return True as we pass IGNORECASE flag."""
    self.assert_(mimic.Regex(r"A", re.IGNORECASE) == "a")

  def testReprWithoutFlags(self):
    """repr should return the regular expression pattern."""
    self.assert_(repr(mimic.Regex(r"a\s+b")) == "<regular expression 'a\s+b'>")

  def testReprWithFlags(self):
    """repr should return the regular expression pattern and flags."""
    self.assert_(repr(mimic.Regex(r"a\s+b", flags=4)) ==
                 "<regular expression 'a\s+b', flags=4>")


class IsTest(unittest.TestCase):
  """Verify Is correctly checks equality based upon identity, not value"""

  class AlwaysComparesTrue(object):
    def __eq__(self, other):
      return True
    def __cmp__(self, other):
      return 0
    def __ne__(self, other):
      return False

  def testEqualityValid(self):
    o1 = self.AlwaysComparesTrue()
    self.assertTrue(mimic.Is(o1), o1)

  def testEqualityInvalid(self):
    o1 = self.AlwaysComparesTrue()
    o2 = self.AlwaysComparesTrue()
    self.assertTrue(o1 == o2)
    # but...
    self.assertFalse(mimic.Is(o1) == o2)

  def testInequalityValid(self):
    o1 = self.AlwaysComparesTrue()
    o2 = self.AlwaysComparesTrue()
    self.assertTrue(mimic.Is(o1) != o2)

  def testInequalityInvalid(self):
    o1 = self.AlwaysComparesTrue()
    self.assertFalse(mimic.Is(o1) != o1)

  def testEqualityInListValid(self):
    o1 = self.AlwaysComparesTrue()
    o2 = self.AlwaysComparesTrue()
    isa_list = [mimic.Is(o1), mimic.Is(o2)]
    str_list = [o1, o2]
    self.assertTrue(isa_list == str_list)

  def testEquailtyInListInvalid(self):
    o1 = self.AlwaysComparesTrue()
    o2 = self.AlwaysComparesTrue()
    isa_list = [mimic.Is(o1), mimic.Is(o2)]
    mixed_list = [o2, o1]
    self.assertFalse(isa_list == mixed_list)


class IsATest(unittest.TestCase):
  """Verify IsA correctly checks equality based upon class type, not value."""

  def testEqualityValid(self):
    """Verify that == correctly identifies objects of the same type."""
    self.assert_(mimic.IsA(str) == 'test')

  def testEqualityInvalid(self):
    """Verify that == correctly identifies objects of different types."""
    self.failIf(mimic.IsA(str) == 10)

  def testInequalityValid(self):
    """Verify that != identifies objects of different type."""
    self.assert_(mimic.IsA(str) != 10)

  def testInequalityInvalid(self):
    """Verify that != correctly identifies objects of the same type."""
    self.failIf(mimic.IsA(str) != "test")

  def testEqualityInListValid(self):
    """Verify list contents are properly compared."""
    isa_list = [mimic.IsA(str), mimic.IsA(str)]
    str_list = ["abc", "def"]
    self.assert_(isa_list == str_list)

  def testEquailtyInListInvalid(self):
    """Verify list contents are properly compared."""
    isa_list = [mimic.IsA(str),mimic.IsA(str)]
    mixed_list = ["abc", 123]
    self.failIf(isa_list == mixed_list)

  def testSpecialTypes(self):
    """Verify that IsA can handle objects like cStringIO.StringIO."""
    isA = mimic.IsA(cStringIO.StringIO())
    stringIO = cStringIO.StringIO()
    self.assert_(isA == stringIO)


class IsAlmostTest(unittest.TestCase):
  """Verify IsAlmost correctly checks equality of floating point numbers."""

  def testEqualityValid(self):
    """Verify that == correctly identifies nearly equivalent floats."""
    self.assertEquals(mimic.IsAlmost(1.8999999999), 1.9)

  def testEqualityInvalid(self):
    """Verify that == correctly identifies non-equivalent floats."""
    self.assertNotEquals(mimic.IsAlmost(1.899), 1.9)

  def testEqualityWithPlaces(self):
    """Verify that specifying places has the desired effect."""
    self.assertNotEquals(mimic.IsAlmost(1.899), 1.9)
    self.assertEquals(mimic.IsAlmost(1.899, places=2), 1.9)

  def testNonNumericTypes(self):
    """Verify that IsAlmost handles non-numeric types properly."""

    self.assertNotEquals(mimic.IsAlmost(1.8999999999), '1.9')
    self.assertNotEquals(mimic.IsAlmost('1.8999999999'), 1.9)
    self.assertNotEquals(mimic.IsAlmost('1.8999999999'), '1.9')


class ValueRememberTest(unittest.TestCase):
  """Verify comparing argument against remembered value."""

  def testValueEquals(self):
    """Verify that value will compare to stored value."""
    value = mimic.Value()
    value.store_value('hello world')
    self.assertEquals(value, 'hello world')

  def testNoValue(self):
    """Verify that uninitialized value does not compare to "empty" values."""
    value = mimic.Value()
    self.assertNotEquals(value, None)
    self.assertNotEquals(value, False)
    self.assertNotEquals(value, 0)
    self.assertNotEquals(value, '')
    self.assertNotEquals(value, ())
    self.assertNotEquals(value, [])
    self.assertNotEquals(value, {})
    self.assertNotEquals(value, object())
    self.assertNotEquals(value, set())

  def testRememberValue(self):
    """Verify that comparing against remember will store argument."""
    value = mimic.Value()
    remember = mimic.Remember(value)
    self.assertNotEquals(value, 'hello world')  # value not yet stored.
    self.assertEquals(remember, 'hello world')  # store value here.
    self.assertEquals(value, 'hello world')     # compare against stored value.


class MockMethodTest(unittest.TestCase):
  """Test class to verify that the MockMethod class is working correctly."""

  def setUp(self):
    self.expected_method = mimic.MockMethod("testMethod", [], [], False)(
        ['original'])
    self.mock_method = mimic.MockMethod("testMethod", [self.expected_method], [],
                                        True)

  def testNameAttribute(self):
    """Should provide a __name__ attribute."""
    self.assertEquals('testMethod', self.mock_method.__name__)

  def testAndReturnNoneByDefault(self):
    """Should return None by default."""
    return_value = self.mock_method(['original'])
    self.assert_(return_value == None)

  def testAndReturnValue(self):
    """Should return a specificed return value."""
    expected_return_value = "test"
    self.expected_method.AndReturn(expected_return_value)
    return_value = self.mock_method(['original'])
    self.assert_(return_value == expected_return_value)

  def testAndRaiseException(self):
    """Should raise a specified exception."""
    expected_exception = Exception('test exception')
    self.expected_method.AndRaise(expected_exception)
    self.assertRaises(Exception, self.mock_method)

  def testWithSideEffects(self):
    """Should call state modifier."""
    local_list = ['original']
    def modifier(mutable_list):
      self.assertTrue(local_list is mutable_list)
      mutable_list[0] = 'mutation'
    self.expected_method.WithSideEffects(modifier).AndReturn(1)
    self.mock_method(local_list)
    self.assertEquals('mutation', local_list[0])

  def testWithReturningSideEffects(self):
    """Should call state modifier and propagate its return value."""
    local_list = ['original']
    expected_return = 'expected_return'
    def modifier_with_return(mutable_list):
      self.assertTrue(local_list is mutable_list)
      mutable_list[0] = 'mutation'
      return expected_return
    self.expected_method.WithSideEffects(modifier_with_return)
    actual_return = self.mock_method(local_list)
    self.assertEquals('mutation', local_list[0])
    self.assertEquals(expected_return, actual_return)

  def testWithReturningSideEffectsWithAndReturn(self):
    """Should call state modifier and ignore its return value."""
    local_list = ['original']
    expected_return = 'expected_return'
    unexpected_return = 'unexpected_return'
    def modifier_with_return(mutable_list):
      self.assertTrue(local_list is mutable_list)
      mutable_list[0] = 'mutation'
      return unexpected_return
    self.expected_method.WithSideEffects(modifier_with_return).AndReturn(
        expected_return)
    actual_return = self.mock_method(local_list)
    self.assertEquals('mutation', local_list[0])
    self.assertEquals(expected_return, actual_return)

  def testEqualityNoParamsEqual(self):
    """Methods with the same name and without params should be equal."""
    expected_method = mimic.MockMethod("testMethod", [], [], False)
    self.assertEqual(self.mock_method, expected_method)

  def testEqualityNoParamsNotEqual(self):
    """Methods with different names and without params should not be equal."""
    expected_method = mimic.MockMethod("otherMethod", [], [], False)
    self.failIfEqual(self.mock_method, expected_method)

  def testEqualityParamsEqual(self):
    """Methods with the same name and parameters should be equal."""
    params = [1, 2, 3]
    expected_method = mimic.MockMethod("testMethod", [], [], False)
    expected_method._params = params

    self.mock_method._params = params
    self.assertEqual(self.mock_method, expected_method)

  def testEqualityParamsNotEqual(self):
    """Methods with the same name and different params should not be equal."""
    expected_method = mimic.MockMethod("testMethod", [], [], False)
    expected_method._params = [1, 2, 3]

    self.mock_method._params = ['a', 'b', 'c']
    self.failIfEqual(self.mock_method, expected_method)

  def testEqualityNamedParamsEqual(self):
    """Methods with the same name and same named params should be equal."""
    named_params = {"input1": "test", "input2": "params"}
    expected_method = mimic.MockMethod("testMethod", [], [], False)
    expected_method._named_params = named_params

    self.mock_method._named_params = named_params
    self.assertEqual(self.mock_method, expected_method)

  def testEqualityNamedParamsNotEqual(self):
    """Methods with the same name and diffnamed params should not be equal."""
    expected_method = mimic.MockMethod("testMethod", [], [], False)
    expected_method._named_params = {"input1": "test", "input2": "params"}

    self.mock_method._named_params = {"input1": "test2", "input2": "params2"}
    self.failIfEqual(self.mock_method, expected_method)

  def testEqualityWrongType(self):
    """Method should not be equal to an object of a different type."""
    self.failIfEqual(self.mock_method, "string?")

  def testObjectEquality(self):
    """Equality of objects should work without a Comparator"""
    instA = TestClass();
    instB = TestClass();

    params = [instA, ]
    expected_method = mimic.MockMethod("testMethod", [], [], False)
    expected_method._params = params

    self.mock_method._params = [instB, ]
    self.assertEqual(self.mock_method, expected_method)

  def testStrConversion(self):
    method = mimic.MockMethod("f", [], [], False)
    method(1, 2, "st", n1=8, n2="st2")
    self.assertEqual(str(method), ("f(1, 2, 'st', n1=8, n2='st2') -> None"))

    method = mimic.MockMethod("testMethod", [], [], False)
    method(1, 2, "only positional")
    self.assertEqual(str(method), "testMethod(1, 2, 'only positional') -> None")

    method = mimic.MockMethod("testMethod", [], [], False)
    method(a=1, b=2, c="only named")
    self.assertEqual(str(method),
                     "testMethod(a=1, b=2, c='only named') -> None")

    method = mimic.MockMethod("testMethod", [], [], False)
    method()
    self.assertEqual(str(method), "testMethod() -> None")

    method = mimic.MockMethod("testMethod", [], [], False)
    method(x="only 1 parameter")
    self.assertEqual(str(method), "testMethod(x='only 1 parameter') -> None")

    method = mimic.MockMethod("testMethod", [], [], False)
    method().AndReturn('return_value')
    self.assertEqual(str(method), "testMethod() -> 'return_value'")

    method = mimic.MockMethod("testMethod", [], [], False)
    method().AndReturn(('a', {1: 2}))
    self.assertEqual(str(method), "testMethod() -> ('a', {1: 2})")


class MockAnythingTest(unittest.TestCase):
  """Verify that the MockAnything class works as expected."""

  def setUp(self):
    self.mock_object = mimic.MockAnything()

  def testRepr(self):
    """Calling repr on a MockAnything instance must work."""
    self.assertEqual('<MockAnything instance>', repr(self.mock_object))

  def testCanMockStr(self):
    self.mock_object.__str__().AndReturn("foo");
    self.mock_object._Replay()
    actual = str(self.mock_object)
    self.mock_object._Verify();
    self.assertEquals("foo", actual)

  def testSetupMode(self):
    """Verify the mock will accept any call."""
    self.mock_object.NonsenseCall()
    self.assert_(len(self.mock_object._expected_calls_queue) == 1)

  def testReplayWithExpectedCall(self):
    """Verify the mock replays method calls as expected."""
    self.mock_object.ValidCall()          # setup method call
    self.mock_object._Replay()            # start replay mode
    self.mock_object.ValidCall()          # make method call

  def testReplayWithUnexpectedCall(self):
    """Unexpected method calls should raise UnexpectedMethodCallError."""
    self.mock_object.ValidCall()          # setup method call
    self.mock_object._Replay()             # start replay mode
    self.assertRaises(mimic.UnexpectedMethodCallError,
                      self.mock_object.OtherValidCall)

  def testVerifyWithCompleteReplay(self):
    """Verify should not raise an exception for a valid replay."""
    self.mock_object.ValidCall()          # setup method call
    self.mock_object._Replay()             # start replay mode
    self.mock_object.ValidCall()          # make method call
    self.mock_object._Verify()

  def testVerifyWithIncompleteReplay(self):
    """Verify should raise an exception if the replay was not complete."""
    self.mock_object.ValidCall()          # setup method call
    self.mock_object._Replay()             # start replay mode
    # ValidCall() is never made
    self.assertRaises(mimic.ExpectedMethodCallsError, self.mock_object._Verify)

  def testSpecialClassMethod(self):
    """Verify should not raise an exception when special methods are used."""
    self.mock_object[1].AndReturn(True)
    self.mock_object._Replay()
    returned_val = self.mock_object[1]
    self.assert_(returned_val)
    self.mock_object._Verify()

  def testNonzero(self):
    """You should be able to use the mock object in an if."""
    self.mock_object._Replay()
    if self.mock_object:
      pass

  def testNotNone(self):
    """Mock should be comparable to None."""
    self.mock_object._Replay()
    if self.mock_object is not None:
      pass

    if self.mock_object is None:
      pass

  def testEquals(self):
    """A mock should be able to compare itself to another object."""
    self.mock_object._Replay()
    self.assertEquals(self.mock_object, self.mock_object)

  def testEqualsMockFailure(self):
    """Verify equals identifies unequal objects."""
    self.mock_object.SillyCall()
    self.mock_object._Replay()
    self.assertNotEquals(self.mock_object, mimic.MockAnything())

  def testEqualsInstanceFailure(self):
    """Verify equals identifies that objects are different instances."""
    self.mock_object._Replay()
    self.assertNotEquals(self.mock_object, TestClass())

  def testNotEquals(self):
    """Verify not equals works."""
    self.mock_object._Replay()
    self.assertFalse(self.mock_object != self.mock_object)

  def testNestedMockCallsRecordedSerially(self):
    """Test that nested calls work when recorded serially."""
    self.mock_object.CallInner().AndReturn(1)
    self.mock_object.CallOuter(1)
    self.mock_object._Replay()

    self.mock_object.CallOuter(self.mock_object.CallInner())

    self.mock_object._Verify()

  def testNestedMockCallsRecordedNested(self):
    """Test that nested cals work when recorded in a nested fashion."""
    self.mock_object.CallOuter(self.mock_object.CallInner().AndReturn(1))
    self.mock_object._Replay()

    self.mock_object.CallOuter(self.mock_object.CallInner())

    self.mock_object._Verify()

  def testIsCallable(self):
    """Test that MockAnything can even mock a simple callable.

    This is handy for "stubbing out" a method in a module with a mock, and
    verifying that it was called.
    """
    self.mock_object().AndReturn('mimic0rd')
    self.mock_object._Replay()

    self.assertEquals('mimic0rd', self.mock_object())

    self.mock_object._Verify()

  def testIsReprable(self):
    """Test that MockAnythings can be repr'd without causing a failure."""
    self.failUnless('MockAnything' in repr(self.mock_object))


class MethodCheckerTest(unittest.TestCase):
  """Tests MockMethod's use of MethodChecker method."""

  def testNoParameters(self):
    method = mimic.MockMethod('NoParameters', [], [], False,
                            CheckCallTestClass.NoParameters)
    method()
    self.assertRaises(AttributeError, method, 1)
    self.assertRaises(AttributeError, method, 1, 2)
    self.assertRaises(AttributeError, method, a=1)
    self.assertRaises(AttributeError, method, 1, b=2)

  def testOneParameter(self):
    method = mimic.MockMethod('OneParameter', [], [], False,
                            CheckCallTestClass.OneParameter)
    self.assertRaises(AttributeError, method)
    method(1)
    method(a=1)
    self.assertRaises(AttributeError, method, b=1)
    self.assertRaises(AttributeError, method, 1, 2)
    self.assertRaises(AttributeError, method, 1, a=2)
    self.assertRaises(AttributeError, method, 1, b=2)

  def testTwoParameters(self):
    method = mimic.MockMethod('TwoParameters', [], [], False,
                            CheckCallTestClass.TwoParameters)
    self.assertRaises(AttributeError, method)
    self.assertRaises(AttributeError, method, 1)
    self.assertRaises(AttributeError, method, a=1)
    self.assertRaises(AttributeError, method, b=1)
    method(1, 2)
    method(1, b=2)
    method(a=1, b=2)
    method(b=2, a=1)
    self.assertRaises(AttributeError, method, b=2, c=3)
    self.assertRaises(AttributeError, method, a=1, b=2, c=3)
    self.assertRaises(AttributeError, method, 1, 2, 3)
    self.assertRaises(AttributeError, method, 1, 2, 3, 4)
    self.assertRaises(AttributeError, method, 3, a=1, b=2)

  def testOneDefaultValue(self):
    method = mimic.MockMethod('OneDefaultValue', [], [], False,
                            CheckCallTestClass.OneDefaultValue)
    method()
    method(1)
    method(a=1)
    self.assertRaises(AttributeError, method, b=1)
    self.assertRaises(AttributeError, method, 1, 2)
    self.assertRaises(AttributeError, method, 1, a=2)
    self.assertRaises(AttributeError, method, 1, b=2)

  def testTwoDefaultValues(self):
    method = mimic.MockMethod('TwoDefaultValues', [], [], False,
                            CheckCallTestClass.TwoDefaultValues)
    self.assertRaises(AttributeError, method)
    self.assertRaises(AttributeError, method, c=3)
    self.assertRaises(AttributeError, method, 1)
    self.assertRaises(AttributeError, method, 1, d=4)
    self.assertRaises(AttributeError, method, 1, d=4, c=3)
    method(1, 2)
    method(a=1, b=2)
    method(1, 2, 3)
    method(1, 2, 3, 4)
    method(1, 2, c=3)
    method(1, 2, c=3, d=4)
    method(1, 2, d=4, c=3)
    method(d=4, c=3, a=1, b=2)
    self.assertRaises(AttributeError, method, 1, 2, 3, 4, 5)
    self.assertRaises(AttributeError, method, 1, 2, e=9)
    self.assertRaises(AttributeError, method, a=1, b=2, e=9)

  def testArgs(self):
    method = mimic.MockMethod('Args', [], [], False, CheckCallTestClass.Args)
    self.assertRaises(AttributeError, method)
    self.assertRaises(AttributeError, method, 1)
    method(1, 2)
    method(a=1, b=2)
    method(1, 2, 3)
    method(1, 2, 3, 4)
    self.assertRaises(AttributeError, method, 1, 2, a=3)
    self.assertRaises(AttributeError, method, 1, 2, c=3)

  def testKwargs(self):
    method = mimic.MockMethod('Kwargs', [], [], False, CheckCallTestClass.Kwargs)
    self.assertRaises(AttributeError, method)
    method(1)
    method(1, 2)
    method(a=1, b=2)
    method(b=2, a=1)
    self.assertRaises(AttributeError, method, 1, 2, 3)
    self.assertRaises(AttributeError, method, 1, 2, a=3)
    method(1, 2, c=3)
    method(a=1, b=2, c=3)
    method(c=3, a=1, b=2)
    method(a=1, b=2, c=3, d=4)
    self.assertRaises(AttributeError, method, 1, 2, 3, 4)

  def testArgsAndKwargs(self):
    method = mimic.MockMethod('ArgsAndKwargs', [], [], False,
                            CheckCallTestClass.ArgsAndKwargs)
    self.assertRaises(AttributeError, method)
    method(1)
    method(1, 2)
    method(1, 2, 3)
    method(a=1)
    method(1, b=2)
    self.assertRaises(AttributeError, method, 1, a=2)
    method(b=2, a=1)
    method(c=3, b=2, a=1)
    method(1, 2, c=3)


class CheckCallTestClass(object):
  def NoParameters(self):
    pass

  def OneParameter(self, a):
    pass

  def TwoParameters(self, a, b):
    pass

  def OneDefaultValue(self, a=1):
    pass

  def TwoDefaultValues(self, a, b, c=1, d=2):
    pass

  def Args(self, a, b, *args):
    pass

  def Kwargs(self, a, b=2, **kwargs):
    pass

  def ArgsAndKwargs(self, a, *args, **kwargs):
    pass


class MockObjectTest(unittest.TestCase):
  """Verify that the MockObject class works as exepcted."""

  def setUp(self):
    self.mock_object = mimic.MockObject(TestClass)

  def testSetupModeWithValidCall(self):
    """Verify the mock object properly mocks a basic method call."""
    self.mock_object.ValidCall()
    self.assert_(len(self.mock_object._expected_calls_queue) == 1)

  def testSetupModeWithInvalidCall(self):
    """UnknownMethodCallError should be raised if a non-member method is called.
    """
    # Note: assertRaises does not catch exceptions thrown by MockObject's
    # __getattr__
    try:
      self.mock_object.InvalidCall()
      self.fail("No exception thrown, expected UnknownMethodCallError")
    except mimic.UnknownMethodCallError:
      pass
    except Exception:
      self.fail("Wrong exception type thrown, expected UnknownMethodCallError")

  def testReplayWithInvalidCall(self):
    """UnknownMethodCallError should be raised if a non-member method is called.
    """
    self.mock_object.ValidCall()          # setup method call
    self.mock_object._Replay()             # start replay mode
    # Note: assertRaises does not catch exceptions thrown by MockObject's
    # __getattr__
    try:
      self.mock_object.InvalidCall()
      self.fail("No exception thrown, expected UnknownMethodCallError")
    except mimic.UnknownMethodCallError:
      pass
    except Exception:
      self.fail("Wrong exception type thrown, expected UnknownMethodCallError")

  def testIsInstance(self):
    """Mock should be able to pass as an instance of the mocked class."""
    self.assert_(isinstance(self.mock_object, TestClass))

  def testFindValidMethods(self):
    """Mock should be able to mock all public methods."""
    self.assert_('ValidCall' in self.mock_object._known_methods)
    self.assert_('OtherValidCall' in self.mock_object._known_methods)
    self.assert_('MyClassMethod' in self.mock_object._known_methods)
    self.assert_('MyStaticMethod' in self.mock_object._known_methods)
    self.assert_('_ProtectedCall' in self.mock_object._known_methods)
    self.assert_('__PrivateCall' not in self.mock_object._known_methods)
    self.assert_('_TestClass__PrivateCall' in self.mock_object._known_methods)

  def testFindsSuperclassMethods(self):
    """Mock should be able to mock superclasses methods."""
    self.mock_object = mimic.MockObject(ChildClass)
    self.assert_('ValidCall' in self.mock_object._known_methods)
    self.assert_('OtherValidCall' in self.mock_object._known_methods)
    self.assert_('MyClassMethod' in self.mock_object._known_methods)
    self.assert_('ChildValidCall' in self.mock_object._known_methods)

  def testAccessClassVariables(self):
    """Class variables should be accessible through the mock."""
    self.assert_('SOME_CLASS_VAR' in self.mock_object._known_vars)
    self.assert_('_PROTECTED_CLASS_VAR' in self.mock_object._known_vars)
    self.assertEquals('test_value', self.mock_object.SOME_CLASS_VAR)

  def testEquals(self):
    """A mock should be able to compare itself to another object."""
    self.mock_object._Replay()
    self.assertEquals(self.mock_object, self.mock_object)

  def testEqualsMockFailure(self):
    """Verify equals identifies unequal objects."""
    self.mock_object.ValidCall()
    self.mock_object._Replay()
    self.assertNotEquals(self.mock_object, mimic.MockObject(TestClass))

  def testEqualsInstanceFailure(self):
    """Verify equals identifies that objects are different instances."""
    self.mock_object._Replay()
    self.assertNotEquals(self.mock_object, TestClass())

  def testNotEquals(self):
    """Verify not equals works."""
    self.mock_object._Replay()
    self.assertFalse(self.mock_object != self.mock_object)

  def testMockSetItem_ExpectedSetItem_Success(self):
    """Test that __setitem__() gets mocked in Dummy.

    In this test, _Verify() succeeds.
    """
    dummy = mimic.MockObject(TestClass)
    dummy['X'] = 'Y'

    dummy._Replay()

    dummy['X'] = 'Y'

    dummy._Verify()

  def testMockSetItem_ExpectedSetItem_NoSuccess(self):
    """Test that __setitem__() gets mocked in Dummy.

    In this test, _Verify() fails.
    """
    dummy = mimic.MockObject(TestClass)
    dummy['X'] = 'Y'

    dummy._Replay()

    # NOT doing dummy['X'] = 'Y'

    self.assertRaises(mimic.ExpectedMethodCallsError, dummy._Verify)

  def testMockSetItem_ExpectedNoSetItem_Success(self):
    """Test that __setitem__() gets mocked in Dummy."""
    dummy = mimic.MockObject(TestClass)
    # NOT doing dummy['X'] = 'Y'

    dummy._Replay()

    def call(): dummy['X'] = 'Y'
    self.assertRaises(mimic.UnexpectedMethodCallError, call)

  def testMockSetItem_ExpectedNoSetItem_NoSuccess(self):
    """Test that __setitem__() gets mocked in Dummy.

    In this test, _Verify() fails.
    """
    dummy = mimic.MockObject(TestClass)
    # NOT doing dummy['X'] = 'Y'

    dummy._Replay()

    # NOT doing dummy['X'] = 'Y'

    dummy._Verify()

  def testMockSetItem_ExpectedSetItem_NonmatchingParameters(self):
    """Test that __setitem__() fails if other parameters are expected."""
    dummy = mimic.MockObject(TestClass)
    dummy['X'] = 'Y'

    dummy._Replay()

    def call(): dummy['wrong'] = 'Y'

    self.assertRaises(mimic.UnexpectedMethodCallError, call)

    self.assertRaises(mimic.SwallowedExceptionError, dummy._Verify)

  def testMockSetItem_WithSubClassOfNewStyleClass(self):
    class NewStyleTestClass(object):
      def __init__(self):
        self.my_dict = {}

      def __setitem__(self, key, value):
        self.my_dict[key], value

    class TestSubClass(NewStyleTestClass):
      pass

    dummy = mimic.MockObject(TestSubClass)
    dummy[1] = 2
    dummy._Replay()
    dummy[1] = 2
    dummy._Verify()

  def testMockGetItem_ExpectedGetItem_Success(self):
    """Test that __getitem__() gets mocked in Dummy.

    In this test, _Verify() succeeds.
    """
    dummy = mimic.MockObject(TestClass)
    dummy['X'].AndReturn('value')

    dummy._Replay()

    self.assertEqual(dummy['X'], 'value')

    dummy._Verify()

  def testMockGetItem_ExpectedGetItem_NoSuccess(self):
    """Test that __getitem__() gets mocked in Dummy.

    In this test, _Verify() fails.
    """
    dummy = mimic.MockObject(TestClass)
    dummy['X'].AndReturn('value')

    dummy._Replay()

    # NOT doing dummy['X']

    self.assertRaises(mimic.ExpectedMethodCallsError, dummy._Verify)

  def testMockGetItem_ExpectedNoGetItem_NoSuccess(self):
    """Test that __getitem__() gets mocked in Dummy."""
    dummy = mimic.MockObject(TestClass)
    # NOT doing dummy['X']

    dummy._Replay()

    def call(): return dummy['X']
    self.assertRaises(mimic.UnexpectedMethodCallError, call)

  def testMockGetItem_ExpectedGetItem_NonmatchingParameters(self):
    """Test that __getitem__() fails if other parameters are expected."""
    dummy = mimic.MockObject(TestClass)
    dummy['X'].AndReturn('value')

    dummy._Replay()

    def call(): return dummy['wrong']

    self.assertRaises(mimic.UnexpectedMethodCallError, call)

    self.assertRaises(mimic.SwallowedExceptionError, dummy._Verify)

  def testMockGetItem_WithSubClassOfNewStyleClass(self):
    class NewStyleTestClass(object):
      def __getitem__(self, key):
        return {1: '1', 2: '2'}[key]

    class TestSubClass(NewStyleTestClass):
      pass

    dummy = mimic.MockObject(TestSubClass)
    dummy[1].AndReturn('3')

    dummy._Replay()
    self.assertEquals('3', dummy.__getitem__(1))
    dummy._Verify()

  def testMockIter_ExpectedIter_Success(self):
    """Test that __iter__() gets mocked in Dummy.

    In this test, _Verify() succeeds.
    """
    dummy = mimic.MockObject(TestClass)
    iter(dummy).AndReturn(iter(['X', 'Y']))

    dummy._Replay()

    self.assertEqual([x for x in dummy], ['X', 'Y'])

    dummy._Verify()

  def testMockContains_ExpectedContains_Success(self):
    """Test that __contains__ gets mocked in Dummy.

    In this test, _Verify() succeeds.
    """
    dummy = mimic.MockObject(TestClass)
    dummy.__contains__('X').AndReturn(True)

    dummy._Replay()

    self.failUnless('X' in dummy)

    dummy._Verify()

  def testMockContains_ExpectedContains_NoSuccess(self):
    """Test that __contains__() gets mocked in Dummy.

    In this test, _Verify() fails.
    """
    dummy = mimic.MockObject(TestClass)
    dummy.__contains__('X').AndReturn('True')

    dummy._Replay()

    # NOT doing 'X' in dummy

    self.assertRaises(mimic.ExpectedMethodCallsError, dummy._Verify)

  def testMockContains_ExpectedContains_NonmatchingParameter(self):
    """Test that __contains__ fails if other parameters are expected."""
    dummy = mimic.MockObject(TestClass)
    dummy.__contains__('X').AndReturn(True)

    dummy._Replay()

    def call(): return 'Y' in dummy

    self.assertRaises(mimic.UnexpectedMethodCallError, call)

    self.assertRaises(mimic.SwallowedExceptionError, dummy._Verify)

  def testMockIter_ExpectedIter_NoSuccess(self):
    """Test that __iter__() gets mocked in Dummy.

    In this test, _Verify() fails.
    """
    dummy = mimic.MockObject(TestClass)
    iter(dummy).AndReturn(iter(['X', 'Y']))

    dummy._Replay()

    # NOT doing self.assertEqual([x for x in dummy], ['X', 'Y'])

    self.assertRaises(mimic.ExpectedMethodCallsError, dummy._Verify)

  def testMockIter_ExpectedNoIter_NoSuccess(self):
    """Test that __iter__() gets mocked in Dummy."""
    dummy = mimic.MockObject(TestClass)
    # NOT doing iter(dummy)

    dummy._Replay()

    def call(): return [x for x in dummy]
    self.assertRaises(mimic.UnexpectedMethodCallError, call)

  def testMockIter_ExpectedGetItem_Success(self):
    """Test that __iter__() gets mocked in Dummy using getitem."""
    dummy = mimic.MockObject(SubscribtableNonIterableClass)
    dummy[0].AndReturn('a')
    dummy[1].AndReturn('b')
    dummy[2].AndRaise(IndexError)

    dummy._Replay()
    self.assertEquals(['a', 'b'], [x for x in dummy])
    dummy._Verify()

  def testMockIter_ExpectedNoGetItem_NoSuccess(self):
    """Test that __iter__() gets mocked in Dummy using getitem."""
    dummy = mimic.MockObject(SubscribtableNonIterableClass)
    # NOT doing dummy[index]

    dummy._Replay()
    function = lambda: [x for x in dummy]
    self.assertRaises(mimic.UnexpectedMethodCallError, function)

  def testMockGetIter_WithSubClassOfNewStyleClass(self):
    class NewStyleTestClass(object):
      def __iter__(self):
        return iter([1, 2, 3])

    class TestSubClass(NewStyleTestClass):
      pass

    dummy = mimic.MockObject(TestSubClass)
    iter(dummy).AndReturn(iter(['a', 'b']))
    dummy._Replay()
    self.assertEquals(['a', 'b'], [x for x in dummy])
    dummy._Verify()

  def testInstantiationWithAdditionalAttributes(self):
    mock_object = mimic.MockObject(TestClass, attrs={"attr1": "value"})
    self.assertEquals(mock_object.attr1, "value")

  def testCantOverrideMethodsWithAttributes(self):
    self.assertRaises(ValueError, mimic.MockObject, TestClass,
                      attrs={"ValidCall": "value"})

  def testCantMockNonPublicAttributes(self):
    self.assertRaises(mimic.PrivateAttributeError, mimic.MockObject, TestClass,
                      attrs={"_protected": "value"})
    self.assertRaises(mimic.PrivateAttributeError, mimic.MockObject, TestClass,
                      attrs={"__private": "value"})


class MimicTest(unittest.TestCase):
  """Verify Mimic works correctly."""

  def setUp(self):
    self.mimic = mimic.Mimic()

  def testCreateObject(self):
    """Mimic should create a mock object."""
    self.mimic.CreateMock(TestClass)

  def testCreateMockOfType(self):
    self.mimic.CreateMock(type)

  def testCreateMockWithBogusAttr(self):

    class BogusAttrClass(object):
      __slots__ = 'no_such_attr',

    foo = BogusAttrClass()
    self.mimic.CreateMock(foo)

  def testVerifyObjectWithCompleteReplay(self):
    """Mimic should replay and verify all objects it created."""
    mock_obj = self.mimic.CreateMock(TestClass)
    mock_obj.ValidCall()
    mock_obj.ValidCallWithArgs(mimic.IsA(TestClass))
    self.mimic.ReplayAll()
    mock_obj.ValidCall()
    mock_obj.ValidCallWithArgs(TestClass("some_value"))
    self.mimic.VerifyAll()

  def testVerifyObjectWithIncompleteReplay(self):
    """Mimic should raise an exception if a mock didn't replay completely."""
    mock_obj = self.mimic.CreateMock(TestClass)
    mock_obj.ValidCall()
    self.mimic.ReplayAll()
    # ValidCall() is never made
    self.assertRaises(mimic.ExpectedMethodCallsError, self.mimic.VerifyAll)

  def testEntireWorkflow(self):
    """Test the whole work flow."""
    mock_obj = self.mimic.CreateMock(TestClass)
    mock_obj.ValidCall().AndReturn("yes")
    self.mimic.ReplayAll()

    ret_val = mock_obj.ValidCall()
    self.assertEquals("yes", ret_val)
    self.mimic.VerifyAll()

  def testSignatureMatchingWithComparatorAsFirstArg(self):
    """Test that the first argument can be a comparator."""

    def VerifyLen(val):
      """This will raise an exception when not given a list.

      This exception will be raised when trying to infer/validate the
      method signature.
      """
      return len(val) != 1

    mock_obj = self.mimic.CreateMock(TestClass)
    # This intentionally does not name the 'nine' param so it triggers
    # deeper inspection.
    mock_obj.MethodWithArgs(mimic.Func(VerifyLen), mimic.IgnoreArg(), None)
    self.mimic.ReplayAll()

    mock_obj.MethodWithArgs([1, 2], "foo", None)

    self.mimic.VerifyAll()

  def testCallableObject(self):
    """Test recording calls to a callable object works."""
    mock_obj = self.mimic.CreateMock(CallableClass)
    mock_obj("foo").AndReturn("qux")
    self.mimic.ReplayAll()

    ret_val = mock_obj("foo")
    self.assertEquals("qux", ret_val)
    self.mimic.VerifyAll()

  def testInheritedCallableObject(self):
    """Test recording calls to an object inheriting from a callable object."""
    mock_obj = self.mimic.CreateMock(InheritsFromCallable)
    mock_obj("foo").AndReturn("qux")
    self.mimic.ReplayAll()

    ret_val = mock_obj("foo")
    self.assertEquals("qux", ret_val)
    self.mimic.VerifyAll()

  def testCallOnNonCallableObject(self):
    """Test that you cannot call a non-callable object."""
    mock_obj = self.mimic.CreateMock(TestClass)
    self.assertRaises(TypeError, mock_obj)

  def testCallableObjectWithBadCall(self):
    """Test verifying calls to a callable object works."""
    mock_obj = self.mimic.CreateMock(CallableClass)
    mock_obj("foo").AndReturn("qux")
    self.mimic.ReplayAll()

    self.assertRaises(mimic.UnexpectedMethodCallError, mock_obj, "ZOOBAZ")

  def testCallableObjectVerifiesSignature(self):
    mock_obj = self.mimic.CreateMock(CallableClass)
    # Too many arguments
    self.assertRaises(AttributeError, mock_obj, "foo", "bar")

  def testUnorderedGroup(self):
    """Test that using one unordered group works."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Method(1).InAnyOrder()
    mock_obj.Method(2).InAnyOrder()
    self.mimic.ReplayAll()

    mock_obj.Method(2)
    mock_obj.Method(1)

    self.mimic.VerifyAll()

  def testUnorderedGroupsInline(self):
    """Unordered groups should work in the context of ordered calls."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(1).InAnyOrder()
    mock_obj.Method(2).InAnyOrder()
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    mock_obj.Method(2)
    mock_obj.Method(1)
    mock_obj.Close()

    self.mimic.VerifyAll()

  def testMultipleUnorderdGroups(self):
    """Multiple unoreded groups should work."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Method(1).InAnyOrder()
    mock_obj.Method(2).InAnyOrder()
    mock_obj.Foo().InAnyOrder('group2')
    mock_obj.Bar().InAnyOrder('group2')
    self.mimic.ReplayAll()

    mock_obj.Method(2)
    mock_obj.Method(1)
    mock_obj.Bar()
    mock_obj.Foo()

    self.mimic.VerifyAll()

  def testMultipleUnorderdGroupsOutOfOrder(self):
    """Multiple unordered groups should maintain external order"""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Method(1).InAnyOrder()
    mock_obj.Method(2).InAnyOrder()
    mock_obj.Foo().InAnyOrder('group2')
    mock_obj.Bar().InAnyOrder('group2')
    self.mimic.ReplayAll()

    mock_obj.Method(2)
    self.assertRaises(mimic.UnexpectedMethodCallError, mock_obj.Bar)

  def testUnorderedGroupWithReturnValue(self):
    """Unordered groups should work with return values."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(1).InAnyOrder().AndReturn(9)
    mock_obj.Method(2).InAnyOrder().AndReturn(10)
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    actual_two = mock_obj.Method(2)
    actual_one = mock_obj.Method(1)
    mock_obj.Close()

    self.assertEquals(9, actual_one)
    self.assertEquals(10, actual_two)

    self.mimic.VerifyAll()

  def testUnorderedGroupWithComparator(self):
    """Unordered groups should work with comparators"""

    def VerifyOne(cmd):
      if not isinstance(cmd, str):
        self.fail('Unexpected type passed to comparator: ' + str(cmd))
      return cmd == 'test'

    def VerifyTwo(cmd):
      return True

    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Foo(['test'], mimic.Func(VerifyOne), bar=1).InAnyOrder().\
        AndReturn('yes test')
    mock_obj.Foo(['test'], mimic.Func(VerifyTwo), bar=1).InAnyOrder().\
        AndReturn('anything')

    self.mimic.ReplayAll()

    mock_obj.Foo(['test'], 'anything', bar=1)
    mock_obj.Foo(['test'], 'test', bar=1)

    self.mimic.VerifyAll()

  def testMultipleTimes(self):
    """Test if MultipleTimesGroup works."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Method(1).MultipleTimes().AndReturn(9)
    mock_obj.Method(2).AndReturn(10)
    mock_obj.Method(3).MultipleTimes().AndReturn(42)
    self.mimic.ReplayAll()

    actual_one = mock_obj.Method(1)
    second_one = mock_obj.Method(1) # This tests MultipleTimes.
    actual_two = mock_obj.Method(2)
    actual_three = mock_obj.Method(3)
    mock_obj.Method(3)
    mock_obj.Method(3)

    self.mimic.VerifyAll()

    self.assertEquals(9, actual_one)
    self.assertEquals(9, second_one) # Repeated calls should return same number.
    self.assertEquals(10, actual_two)
    self.assertEquals(42, actual_three)

  def testMultipleTimesUsingIsAParameter(self):
    """Test if MultipleTimesGroup works with a IsA parameter."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(mimic.IsA(str)).MultipleTimes("IsA").AndReturn(9)
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    actual_one = mock_obj.Method("1")
    second_one = mock_obj.Method("2") # This tests MultipleTimes.
    mock_obj.Close()

    self.mimic.VerifyAll()

    self.assertEquals(9, actual_one)
    self.assertEquals(9, second_one) # Repeated calls should return same number.

  def testMutlipleTimesUsingFunc(self):
    """Test that the Func is not evaluated more times than necessary.

    If a Func() has side effects, it can cause a passing test to fail.
    """

    self.counter = 0
    def MyFunc(actual_str):
      """Increment the counter if actual_str == 'foo'."""
      if actual_str == 'foo':
        self.counter += 1
      return True

    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(mimic.Func(MyFunc)).MultipleTimes()
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    mock_obj.Method('foo')
    mock_obj.Method('foo')
    mock_obj.Method('not-foo')
    mock_obj.Close()

    self.mimic.VerifyAll()

    self.assertEquals(2, self.counter)

  def testMultipleTimesThreeMethods(self):
    """Test if MultipleTimesGroup works with three or more methods."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(1).MultipleTimes().AndReturn(9)
    mock_obj.Method(2).MultipleTimes().AndReturn(8)
    mock_obj.Method(3).MultipleTimes().AndReturn(7)
    mock_obj.Method(4).AndReturn(10)
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    actual_three = mock_obj.Method(3)
    mock_obj.Method(1)
    actual_two = mock_obj.Method(2)
    mock_obj.Method(3)
    actual_one = mock_obj.Method(1)
    actual_four = mock_obj.Method(4)
    mock_obj.Close()

    self.assertEquals(9, actual_one)
    self.assertEquals(8, actual_two)
    self.assertEquals(7, actual_three)
    self.assertEquals(10, actual_four)

    self.mimic.VerifyAll()

  def testMultipleTimesMissingOne(self):
    """Test if MultipleTimesGroup fails if one method is missing."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(1).MultipleTimes().AndReturn(9)
    mock_obj.Method(2).MultipleTimes().AndReturn(8)
    mock_obj.Method(3).MultipleTimes().AndReturn(7)
    mock_obj.Method(4).AndReturn(10)
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    mock_obj.Method(3)
    mock_obj.Method(2)
    mock_obj.Method(3)
    mock_obj.Method(3)
    mock_obj.Method(2)

    self.assertRaises(mimic.UnexpectedMethodCallError, mock_obj.Method, 4)

  def testMultipleTimesTwoGroups(self):
    """Test if MultipleTimesGroup works with a group after a
    MultipleTimesGroup.
    """
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(1).MultipleTimes().AndReturn(9)
    mock_obj.Method(3).MultipleTimes("nr2").AndReturn(42)
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    actual_one = mock_obj.Method(1)
    mock_obj.Method(1)
    actual_three = mock_obj.Method(3)
    mock_obj.Method(3)
    mock_obj.Close()

    self.assertEquals(9, actual_one)
    self.assertEquals(42, actual_three)

    self.mimic.VerifyAll()

  def testMultipleTimesTwoGroupsFailure(self):
    """Test if MultipleTimesGroup fails with a group after a
    MultipleTimesGroup.
    """
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    mock_obj.Method(1).MultipleTimes().AndReturn(9)
    mock_obj.Method(3).MultipleTimes("nr2").AndReturn(42)
    mock_obj.Close()
    self.mimic.ReplayAll()

    mock_obj.Open()
    actual_one = mock_obj.Method(1)
    mock_obj.Method(1)
    actual_three = mock_obj.Method(3)

    self.assertRaises(mimic.UnexpectedMethodCallError, mock_obj.Method, 1)

  def testWithSideEffects(self):
    """Test side effect operations actually modify their target objects."""
    def modifier(mutable_list):
      mutable_list[0] = 'mutated'
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.ConfigureInOutParameter(['original']).WithSideEffects(modifier)
    mock_obj.WorkWithParameter(['mutated'])
    self.mimic.ReplayAll()

    local_list = ['original']
    mock_obj.ConfigureInOutParameter(local_list)
    mock_obj.WorkWithParameter(local_list)

    self.mimic.VerifyAll()

  def testWithSideEffectsException(self):
    """Test side effect operations actually modify their target objects."""
    def modifier(mutable_list):
      mutable_list[0] = 'mutated'
    mock_obj = self.mimic.CreateMockAnything()
    method = mock_obj.ConfigureInOutParameter(['original'])
    method.WithSideEffects(modifier).AndRaise(Exception('exception'))
    mock_obj.WorkWithParameter(['mutated'])
    self.mimic.ReplayAll()

    local_list = ['original']
    self.failUnlessRaises(Exception,
                          mock_obj.ConfigureInOutParameter,
                          local_list)
    mock_obj.WorkWithParameter(local_list)

    self.mimic.VerifyAll()

  def testStubOutMethod(self):
    """Test that a method is replaced with a MockObject."""
    test_obj = TestClass()
    method_type = type(test_obj.OtherValidCall)
    # Replace OtherValidCall with a mock.
    self.mimic.StubOutWithMock(test_obj, 'OtherValidCall')
    self.assertTrue(isinstance(test_obj.OtherValidCall, mimic.MockObject))
    self.assertFalse(type(test_obj.OtherValidCall) is method_type)

    test_obj.OtherValidCall().AndReturn('foo')
    self.mimic.ReplayAll()

    actual = test_obj.OtherValidCall()

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()
    self.assertEquals('foo', actual)
    self.assertTrue(type(test_obj.OtherValidCall) is method_type)

  def testStubOutMethod_Unbound_Comparator(self):
    instance = TestClass()
    self.mimic.StubOutWithMock(TestClass, 'OtherValidCall')

    TestClass.OtherValidCall(mimic.IgnoreArg()).AndReturn('foo')
    self.mimic.ReplayAll()

    actual = TestClass.OtherValidCall(instance)

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()
    self.assertEquals('foo', actual)

  def testStubOutMethod_Unbound_Subclass_Comparator(self):
    self.mimic.StubOutWithMock(mimic_test_helper.TestClassFromAnotherModule,
                             'Value')
    mimic_test_helper.TestClassFromAnotherModule.Value(
        mimic.IsA(mimic_test_helper.ChildClassFromAnotherModule)).AndReturn('foo')
    self.mimic.ReplayAll()

    instance = mimic_test_helper.ChildClassFromAnotherModule()
    actual = mimic_test_helper.TestClassFromAnotherModule.Value(instance)

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()
    self.assertEquals('foo', actual)

  def testStubOuMethod_Unbound_WithOptionalParams(self):
    self.mimic = mimic.Mimic()
    self.mimic.StubOutWithMock(TestClass, 'OptionalArgs')
    TestClass.OptionalArgs(mimic.IgnoreArg(), foo=2)
    self.mimic.ReplayAll()

    t = TestClass()
    TestClass.OptionalArgs(t, foo=2)

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutMethod_Unbound_ActualInstance(self):
    instance = TestClass()
    self.mimic.StubOutWithMock(TestClass, 'OtherValidCall')

    TestClass.OtherValidCall(instance).AndReturn('foo')
    self.mimic.ReplayAll()

    actual = TestClass.OtherValidCall(instance)

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()
    self.assertEquals('foo', actual)

  def testStubOutMethod_Unbound_DifferentInstance(self):
    instance = TestClass()
    self.mimic.StubOutWithMock(TestClass, 'OtherValidCall')

    TestClass.OtherValidCall(instance).AndReturn('foo')
    self.mimic.ReplayAll()

    # This should fail, since the instances are different
    self.assertRaises(mimic.UnexpectedMethodCallError,
                      TestClass.OtherValidCall, "wrong self")

    self.assertRaises(mimic.SwallowedExceptionError, self.mimic.VerifyAll)
    self.mimic.UnsetStubs()

  def testStubOutMethod_Unbound_NamedUsingPositional(self):
    """Check positional parameters can be matched to keyword arguments."""
    self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, 'NamedParams')
    instance = mimic_test_helper.ExampleClass()
    mimic_test_helper.ExampleClass.NamedParams(instance, 'foo', baz=None)
    self.mimic.ReplayAll()

    mimic_test_helper.ExampleClass.NamedParams(instance, 'foo', baz=None)

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutMethod_Unbound_NamedUsingPositional_SomePositional(self):
    """Check positional parameters can be matched to keyword arguments."""
    self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, 'TestMethod')
    instance = mimic_test_helper.ExampleClass()
    mimic_test_helper.ExampleClass.TestMethod(instance, 'one', 'two', 'nine')
    self.mimic.ReplayAll()

    mimic_test_helper.ExampleClass.TestMethod(instance, 'one', 'two', 'nine')

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutMethod_Unbound_SpecialArgs(self):
    self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, 'SpecialArgs')
    instance = mimic_test_helper.ExampleClass()
    mimic_test_helper.ExampleClass.SpecialArgs(instance, 'foo', None, bar='bar')
    self.mimic.ReplayAll()

    mimic_test_helper.ExampleClass.SpecialArgs(instance, 'foo', None, bar='bar')

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutMethod_Bound_SimpleTest(self):
    t = self.mimic.CreateMock(TestClass)

    t.MethodWithArgs(mimic.IgnoreArg(), mimic.IgnoreArg()).AndReturn('foo')
    self.mimic.ReplayAll()

    actual = t.MethodWithArgs(None, None);

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()
    self.assertEquals('foo', actual)

  def testStubOutMethod_Bound_NamedUsingPositional(self):
    """Check positional parameters can be matched to keyword arguments."""
    self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, 'NamedParams')
    instance = mimic_test_helper.ExampleClass()
    instance.NamedParams('foo', baz=None)
    self.mimic.ReplayAll()

    instance.NamedParams('foo', baz=None)

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutMethod_Bound_NamedUsingPositional_SomePositional(self):
    """Check positional parameters can be matched to keyword arguments."""
    self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, 'TestMethod')
    instance = mimic_test_helper.ExampleClass()
    instance.TestMethod(instance, 'one', 'two', 'nine')
    self.mimic.ReplayAll()

    instance.TestMethod(instance, 'one', 'two', 'nine')

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutMethod_Bound_SpecialArgs(self):
    self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, 'SpecialArgs')
    instance = mimic_test_helper.ExampleClass()
    instance.SpecialArgs(instance, 'foo', None, bar='bar')
    self.mimic.ReplayAll()

    instance.SpecialArgs(instance, 'foo', None, bar='bar')

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutMethod_Func_PropgatesExceptions(self):
    """Errors in a Func comparator should propagate to the calling method."""
    class TestException(Exception):
      pass

    def raiseExceptionOnNotOne(value):
      if value == 1:
        return True
      else:
        raise TestException

    test_obj = TestClass()
    self.mimic.StubOutWithMock(test_obj, 'MethodWithArgs')
    test_obj.MethodWithArgs(
        mimic.IgnoreArg(), mimic.Func(raiseExceptionOnNotOne)).AndReturn(1)
    test_obj.MethodWithArgs(
        mimic.IgnoreArg(), mimic.Func(raiseExceptionOnNotOne)).AndReturn(1)
    self.mimic.ReplayAll()

    self.assertEqual(test_obj.MethodWithArgs('ignored', 1), 1)
    self.assertRaises(TestException,
                      test_obj.MethodWithArgs, 'ignored', 2)

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()


  def testStubOut_SignatureMatching_init_(self):
    self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, '__init__')
    mimic_test_helper.ExampleClass.__init__(mimic.IgnoreArg())
    self.mimic.ReplayAll()

    # Create an instance of a child class, which calls the parent
    # __init__
    mimic_test_helper.ChildExampleClass()

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

  def testStubOutClass_OldStyle(self):
    """Test a mocked class whose __init__ returns a Mock."""
    self.mimic.StubOutWithMock(mimic_test_helper, 'TestClassFromAnotherModule')
    self.assert_(isinstance(mimic_test_helper.TestClassFromAnotherModule,
                            mimic.MockObject))

    mock_instance = self.mimic.CreateMock(
        mimic_test_helper.TestClassFromAnotherModule)
    mimic_test_helper.TestClassFromAnotherModule().AndReturn(mock_instance)
    mock_instance.Value().AndReturn('mock instance')

    self.mimic.ReplayAll()

    a_mock = mimic_test_helper.TestClassFromAnotherModule()
    actual = a_mock.Value()

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()
    self.assertEquals('mock instance', actual)

  def testStubOutClass(self):
    self.mimic.StubOutClassWithMocks(mimic_test_helper, 'CallableClass')

    # Instance one
    mock_one = mimic_test_helper.CallableClass(1, 2)
    mock_one.Value().AndReturn('mock')

    # Instance two
    mock_two = mimic_test_helper.CallableClass(8, 9)
    mock_two('one').AndReturn('called mock')

    self.mimic.ReplayAll()

    one = mimic_test_helper.CallableClass(1, 2)
    actual_one = one.Value()

    two = mimic_test_helper.CallableClass(8, 9)
    actual_two = two('one')

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()

    # Verify the correct mocks were returned
    self.assertEquals(mock_one, one)
    self.assertEquals(mock_two, two)

    # Verify
    self.assertEquals('mock', actual_one)
    self.assertEquals('called mock', actual_two)

  try:
    import abc
    # I'd use the unittest skipping decorators for this but I want to support
    # older versions of Python that don't have them.
    def testStubOutClass_ABCMeta(self):
      self.mimic.StubOutClassWithMocks(mimic_test_helper,
                                     'CallableSubclassOfMyDictABC')
      mock_foo = mimic_test_helper.CallableSubclassOfMyDictABC(foo='!mock bar')
      mock_foo['foo'].AndReturn('mock bar')
      mock_spam = mimic_test_helper.CallableSubclassOfMyDictABC(spam='!mock eggs')
      mock_spam('beans').AndReturn('called mock')

      self.mimic.ReplayAll()

      foo = mimic_test_helper.CallableSubclassOfMyDictABC(foo='!mock bar')
      actual_foo_bar = foo['foo']

      spam = mimic_test_helper.CallableSubclassOfMyDictABC(spam='!mock eggs')
      actual_spam = spam('beans')

      self.mimic.VerifyAll()
      self.mimic.UnsetStubs()

      # Verify the correct mocks were returned
      self.assertEquals(mock_foo, foo)
      self.assertEquals(mock_spam, spam)

      # Verify
      self.assertEquals('mock bar', actual_foo_bar)
      self.assertEquals('called mock', actual_spam)
  except ImportError:
    print >>sys.stderr, "testStubOutClass_ABCMeta. ... Skipped - no abc module"

  def testStubOutClass_NotAClass(self):
    self.assertRaises(TypeError, self.mimic.StubOutClassWithMocks,
                      mimic_test_helper, 'MyTestFunction')

  def testStubOutClassNotEnoughCreated(self):
    self.mimic.StubOutClassWithMocks(mimic_test_helper, 'CallableClass')

    mimic_test_helper.CallableClass(1, 2)
    mimic_test_helper.CallableClass(8, 9)

    self.mimic.ReplayAll()
    mimic_test_helper.CallableClass(1, 2)

    self.assertRaises(mimic.ExpectedMockCreationError, self.mimic.VerifyAll)
    self.mimic.UnsetStubs()

  def testStubOutClassWrongSignature(self):
    self.mimic.StubOutClassWithMocks(mimic_test_helper, 'CallableClass')

    self.assertRaises(AttributeError, mimic_test_helper.CallableClass)

    self.mimic.UnsetStubs()

  def testStubOutClassWrongParameters(self):
    self.mimic.StubOutClassWithMocks(mimic_test_helper, 'CallableClass')

    mimic_test_helper.CallableClass(1, 2)

    self.mimic.ReplayAll()

    self.assertRaises(mimic.UnexpectedMethodCallError,
                      mimic_test_helper.CallableClass, 8, 9)
    self.mimic.UnsetStubs()

  def testStubOutClassTooManyCreated(self):
    self.mimic.StubOutClassWithMocks(mimic_test_helper, 'CallableClass')

    mimic_test_helper.CallableClass(1, 2)

    self.mimic.ReplayAll()
    mimic_test_helper.CallableClass(1, 2)
    self.assertRaises(mimic.UnexpectedMockCreationError,
                      mimic_test_helper.CallableClass, 8, 9)

    self.mimic.UnsetStubs()

  def testWarnsUserIfMockingMock(self):
    """Test that user is warned if they try to stub out a MockAnything."""
    self.mimic.StubOutWithMock(TestClass, 'MyStaticMethod')
    self.assertRaises(TypeError, self.mimic.StubOutWithMock, TestClass,
                      'MyStaticMethod')

  def testStubOutFirstClassMethodVerifiesSignature(self):
    self.mimic.StubOutWithMock(mimic_test_helper, 'MyTestFunction')

    # Wrong number of arguments
    self.assertRaises(AttributeError, mimic_test_helper.MyTestFunction, 1)
    self.mimic.UnsetStubs()

  def _testMethodSignatureVerification(self, stubClass):
    # If stubClass is true, the test is run against an a stubbed out class,
    # else the test is run against a stubbed out instance.
    if stubClass:
      self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, "TestMethod")
      obj = mimic_test_helper.ExampleClass()
    else:
      obj = mimic_test_helper.ExampleClass()
      self.mimic.StubOutWithMock(mimic_test_helper.ExampleClass, "TestMethod")
    self.assertRaises(AttributeError, obj.TestMethod)
    self.assertRaises(AttributeError, obj.TestMethod, 1)
    self.assertRaises(AttributeError, obj.TestMethod, nine=2)
    obj.TestMethod(1, 2)
    obj.TestMethod(1, 2, 3)
    obj.TestMethod(1, 2, nine=3)
    self.assertRaises(AttributeError, obj.TestMethod, 1, 2, 3, 4)
    self.mimic.UnsetStubs()

  def testStubOutClassMethodVerifiesSignature(self):
    self._testMethodSignatureVerification(stubClass=True)

  def testStubOutObjectMethodVerifiesSignature(self):
    self._testMethodSignatureVerification(stubClass=False)

  def testStubOutObject(self):
    """Test than object is replaced with a Mock."""

    class Foo(object):
      def __init__(self):
        self.obj = TestClass()

    foo = Foo()
    self.mimic.StubOutWithMock(foo, "obj")
    self.assert_(isinstance(foo.obj, mimic.MockObject))
    foo.obj.ValidCall()
    self.mimic.ReplayAll()

    foo.obj.ValidCall()

    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()
    self.failIf(isinstance(foo.obj, mimic.MockObject))

  def testForgotReplayHelpfulMessage(self):
    """If there is an AttributeError on a MockMethod, give users a helpful msg.
    """
    foo = self.mimic.CreateMockAnything()
    bar = self.mimic.CreateMockAnything()
    foo.GetBar().AndReturn(bar)
    bar.ShowMeTheMoney()
    # Forgot to replay!
    try:
      foo.GetBar().ShowMeTheMoney()
    except AttributeError, e:
      self.assertEquals('MockMethod has no attribute "ShowMeTheMoney". '
          'Did you remember to put your mocks in replay mode?', str(e))

  def testSwallowedUnknownMethodCall(self):
    """Test that a swallowed UnknownMethodCallError will be re-raised."""
    dummy = self.mimic.CreateMock(TestClass)
    dummy._Replay()

    def call():
      try:
        dummy.InvalidCall()
      except mimic.UnknownMethodCallError:
        pass

    # UnknownMethodCallError swallowed
    call()

    self.assertRaises(mimic.SwallowedExceptionError, self.mimic.VerifyAll)

  def testSwallowedUnexpectedMockCreation(self):
    """Test that a swallowed UnexpectedMockCreationError will be re-raised."""
    self.mimic.StubOutClassWithMocks(mimic_test_helper, 'CallableClass')
    self.mimic.ReplayAll()

    def call():
      try:
        mimic_test_helper.CallableClass(1, 2)
      except mimic.UnexpectedMockCreationError:
        pass

    # UnexpectedMockCreationError swallowed
    call()

    self.assertRaises(mimic.SwallowedExceptionError, self.mimic.VerifyAll)
    self.mimic.UnsetStubs()

  def testSwallowedUnexpectedMethodCall_WrongMethod(self):
    """Test that a swallowed UnexpectedMethodCallError will be re-raised.

    This case is an extraneous method call."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    self.mimic.ReplayAll()

    def call():
      mock_obj.Open()
      try:
        mock_obj.Close()
      except mimic.UnexpectedMethodCallError:
        pass

    # UnexpectedMethodCall swallowed
    call()

    self.assertRaises(mimic.SwallowedExceptionError, self.mimic.VerifyAll)

  def testSwallowedUnexpectedMethodCall_WrongArguments(self):
    """Test that a swallowed UnexpectedMethodCallError will be re-raised.

    This case is an extraneous method call."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open()
    self.mimic.ReplayAll()

    def call():
      try:
        mock_obj.Open(1)
      except mimic.UnexpectedMethodCallError:
        pass

    # UnexpectedMethodCall swallowed
    call()

    self.assertRaises(mimic.SwallowedExceptionError, self.mimic.VerifyAll)

  def testSwallowedUnexpectedMethodCall_UnorderedGroup(self):
    """Test that a swallowed UnexpectedMethodCallError will be re-raised.

    This case is an extraneous method call in an unordered group."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open().InAnyOrder()
    mock_obj.Close().InAnyOrder()
    self.mimic.ReplayAll()

    def call():
      mock_obj.Close()
      try:
        mock_obj.Open(1)
      except mimic.UnexpectedMethodCallError:
        pass

    # UnexpectedMethodCall swallowed
    call()

    self.assertRaises(mimic.SwallowedExceptionError, self.mimic.VerifyAll)

  def testSwallowedUnexpectedMethodCall_MultipleTimesGroup(self):
    """Test that a swallowed UnexpectedMethodCallError will be re-raised.

    This case is an extraneous method call in a multiple times group."""
    mock_obj = self.mimic.CreateMockAnything()
    mock_obj.Open().MultipleTimes()
    self.mimic.ReplayAll()

    def call():
      try:
        mock_obj.Open(1)
      except mimic.UnexpectedMethodCallError:
        pass

    # UnexpectedMethodCall swallowed
    call()

    self.assertRaises(mimic.SwallowedExceptionError, self.mimic.VerifyAll)


class ReplayTest(unittest.TestCase):
  """Verify Replay works properly."""

  def testReplay(self):
    """Replay should put objects into replay mode."""
    mock_obj = mimic.MockObject(TestClass)
    self.assertFalse(mock_obj._replay_mode)
    mimic.Replay(mock_obj)
    self.assertTrue(mock_obj._replay_mode)


class MimicTestBaseTest(unittest.TestCase):
  """Verify that all tests in a class derived from MimicTestBase are wrapped."""

  def setUp(self):
    self.mimic = mimic.Mimic()
    self.test_mimic = mimic.Mimic()
    self.test_stubs = mimic.stubout.StubOutForTesting()
    self.result = unittest.TestResult()

  def tearDown(self):
    self.mimic.UnsetStubs()
    self.test_mimic.UnsetStubs()
    self.test_stubs.UnsetAll()
    self.test_stubs.SmartUnsetAll()

  def _setUpTestClass(self):
    """Replacement for setUp in the test class instance.

    Assigns a mimic.Mimic instance as the mimic attribute of the test class instance.
    This replacement Mimic instance is under our control before setUp is called
    in the test class instance.
    """
    self.test.mimic = self.test_mimic
    self.test.stubs = self.test_stubs

  def _CreateTest(self, test_name):
    """Create a test from our example mimic class.

    The created test instance is assigned to this instances test attribute.
    """
    self.test = mimic_test_helper.ExampleMimicTest(test_name)
    self.mimic.stubs.Set(self.test, 'setUp', self._setUpTestClass)

  def _VerifySuccess(self):
    """Run the checks to confirm test method completed successfully."""
    self.mimic.StubOutWithMock(self.test_mimic, 'UnsetStubs')
    self.mimic.StubOutWithMock(self.test_mimic, 'VerifyAll')
    self.mimic.StubOutWithMock(self.test_stubs, 'UnsetAll')
    self.mimic.StubOutWithMock(self.test_stubs, 'SmartUnsetAll')
    self.test_mimic.UnsetStubs()
    self.test_mimic.VerifyAll()
    self.test_stubs.UnsetAll()
    self.test_stubs.SmartUnsetAll()
    self.mimic.ReplayAll()
    self.test.run(result=self.result)
    self.assertTrue(self.result.wasSuccessful())
    self.mimic.VerifyAll()
    self.mimic.UnsetStubs()  # Needed to call the real VerifyAll() below.
    self.test_mimic.VerifyAll()

  def testSuccess(self):
    """Successful test method execution test."""
    self._CreateTest('testSuccess')
    self._VerifySuccess()

  def testSuccessNoMocks(self):
    """Let testSuccess() unset all the mocks, and verify they've been unset."""
    self._CreateTest('testSuccess')
    self.test.run(result=self.result)
    self.assertTrue(self.result.wasSuccessful())
    self.assertEqual(OS_LISTDIR, mimic_test_helper.os.listdir)

  def testStubs(self):
    """Test that "self.stubs" is provided as is useful."""
    self._CreateTest('testHasStubs')
    self._VerifySuccess()

  def testStubsNoMocks(self):
    """Let testHasStubs() unset the stubs by itself."""
    self._CreateTest('testHasStubs')
    self.test.run(result=self.result)
    self.assertTrue(self.result.wasSuccessful())
    self.assertEqual(OS_LISTDIR, mimic_test_helper.os.listdir)

  def testExpectedNotCalled(self):
    """Stubbed out method is not called."""
    self._CreateTest('testExpectedNotCalled')
    self.mimic.StubOutWithMock(self.test_mimic, 'UnsetStubs')
    self.mimic.StubOutWithMock(self.test_stubs, 'UnsetAll')
    self.mimic.StubOutWithMock(self.test_stubs, 'SmartUnsetAll')
    # Don't stub out VerifyAll - that's what causes the test to fail
    self.test_mimic.UnsetStubs()
    self.test_stubs.UnsetAll()
    self.test_stubs.SmartUnsetAll()
    self.mimic.ReplayAll()
    self.test.run(result=self.result)
    self.failIf(self.result.wasSuccessful())
    self.mimic.VerifyAll()

  def testExpectedNotCalledNoMocks(self):
    """Let testExpectedNotCalled() unset all the mocks by itself."""
    self._CreateTest('testExpectedNotCalled')
    self.test.run(result=self.result)
    self.failIf(self.result.wasSuccessful())
    self.assertEqual(OS_LISTDIR, mimic_test_helper.os.listdir)

  def testUnexpectedCall(self):
    """Stubbed out method is called with unexpected arguments."""
    self._CreateTest('testUnexpectedCall')
    self.mimic.StubOutWithMock(self.test_mimic, 'UnsetStubs')
    self.mimic.StubOutWithMock(self.test_stubs, 'UnsetAll')
    self.mimic.StubOutWithMock(self.test_stubs, 'SmartUnsetAll')
    # Ensure no calls are made to VerifyAll()
    self.mimic.StubOutWithMock(self.test_mimic, 'VerifyAll')
    self.test_mimic.UnsetStubs()
    self.test_stubs.UnsetAll()
    self.test_stubs.SmartUnsetAll()
    self.mimic.ReplayAll()
    self.test.run(result=self.result)
    self.failIf(self.result.wasSuccessful())
    self.mimic.VerifyAll()

  def testFailure(self):
    """Failing assertion in test method."""
    self._CreateTest('testFailure')
    self.mimic.StubOutWithMock(self.test_mimic, 'UnsetStubs')
    self.mimic.StubOutWithMock(self.test_stubs, 'UnsetAll')
    self.mimic.StubOutWithMock(self.test_stubs, 'SmartUnsetAll')
    # Ensure no calls are made to VerifyAll()
    self.mimic.StubOutWithMock(self.test_mimic, 'VerifyAll')
    self.test_mimic.UnsetStubs()
    self.test_stubs.UnsetAll()
    self.test_stubs.SmartUnsetAll()
    self.mimic.ReplayAll()
    self.test.run(result=self.result)
    self.failIf(self.result.wasSuccessful())
    self.mimic.VerifyAll()

  def testMixin(self):
    """Run test from mix-in test class, ensure it passes."""
    self._CreateTest('testStat')
    self._VerifySuccess()

  def testMixinAgain(self):
    """Run same test as above but from the current test class.

    This ensures metaclass properly wrapped test methods from all base classes.
    If unsetting of stubs doesn't happen, this will fail.
    """
    self._CreateTest('testStatOther')
    self._VerifySuccess()


class VerifyTest(unittest.TestCase):
  """Verify Verify works properly."""

  def testVerify(self):
    """Verify should be called for all objects.

    This should throw an exception because the expected behavior did not occur.
    """
    mock_obj = mimic.MockObject(TestClass)
    mock_obj.ValidCall()
    mock_obj._Replay()
    self.assertRaises(mimic.ExpectedMethodCallsError, mimic.Verify, mock_obj)


class ResetTest(unittest.TestCase):
  """Verify Reset works properly."""

  def testReset(self):
    """Should empty all queues and put mocks in record mode."""
    mock_obj = mimic.MockObject(TestClass)
    mock_obj.ValidCall()
    self.assertFalse(mock_obj._replay_mode)
    mock_obj._Replay()
    self.assertTrue(mock_obj._replay_mode)
    self.assertEquals(1, len(mock_obj._expected_calls_queue))

    mimic.Reset(mock_obj)
    self.assertFalse(mock_obj._replay_mode)
    self.assertEquals(0, len(mock_obj._expected_calls_queue))


class MyTestCase(unittest.TestCase):
  """Simulate the use of a fake wrapper around Python's unittest library."""

  def setUp(self):
    super(MyTestCase, self).setUp()
    self.critical_variable = 42
    self.another_critical_variable = 42

  def testMethodOverride(self):
    """Should be properly overriden in a derived class."""
    self.assertEquals(42, self.another_critical_variable)
    self.another_critical_variable += 1


class MimicTestBaseMultipleInheritanceTest(mimic.MimicTestBase, MyTestCase):
  """Test that multiple inheritance can be used with MimicTestBase."""

  def setUp(self):
    super(MimicTestBaseMultipleInheritanceTest, self).setUp()
    self.another_critical_variable = 99

  def testMultipleInheritance(self):
    """Should be able to access members created by all parent setUp()."""
    self.assert_(isinstance(self.mimic, mimic.Mimic))
    self.assertEquals(42, self.critical_variable)

  def testMethodOverride(self):
    """Should run before MyTestCase.testMethodOverride."""
    self.assertEquals(99, self.another_critical_variable)
    self.another_critical_variable = 42
    super(MimicTestBaseMultipleInheritanceTest, self).testMethodOverride()
    self.assertEquals(43, self.another_critical_variable)

class MimicTestDontMockProperties(MimicTestBaseTest):
    def testPropertiesArentMocked(self):
        mock_class = self.mimic.CreateMock(ClassWithProperties)
        self.assertRaises(mimic.UnknownMethodCallError, lambda:
                mock_class.prop_attr)


class TestClass:
  """This class is used only for testing the mock framework"""

  SOME_CLASS_VAR = "test_value"
  _PROTECTED_CLASS_VAR = "protected value"

  def __init__(self, ivar=None):
    self.__ivar = ivar

  def __eq__(self, rhs):
    return self.__ivar == rhs

  def __ne__(self, rhs):
    return not self.__eq__(rhs)

  def ValidCall(self):
    pass

  def MethodWithArgs(self, one, two, nine=None):
    pass

  def OtherValidCall(self):
    pass

  def OptionalArgs(self, foo='boom'):
    pass

  def ValidCallWithArgs(self, *args, **kwargs):
    pass

  @classmethod
  def MyClassMethod(cls):
    pass

  @staticmethod
  def MyStaticMethod():
    pass

  def _ProtectedCall(self):
    pass

  def __PrivateCall(self):
    pass

  def __getitem__(self, key):
    pass

  def __DoNotMock(self):
    pass

  def __getitem__(self, key):
    """Return the value for key."""
    return self.d[key]

  def __setitem__(self, key, value):
    """Set the value for key to value."""
    self.d[key] = value

  def __contains__(self, key):
     """Returns True if d contains the key."""
     return key in self.d

  def __iter__(self):
    pass


class ChildClass(TestClass):
  """This inherits from TestClass."""
  def __init__(self):
    TestClass.__init__(self)

  def ChildValidCall(self):
    pass


class CallableClass(object):
  """This class is callable, and that should be mockable!"""

  def __init__(self):
    pass

  def __call__(self, param):
    return param

class ClassWithProperties(object):
    def setter_attr(self, value):
        pass

    def getter_attr(self):
        pass

    prop_attr = property(getter_attr, setter_attr)


class SubscribtableNonIterableClass(object):
  def __getitem__(self, index):
    raise IndexError


class InheritsFromCallable(CallableClass):
  """This class should also be mockable; it inherits from a callable class."""

  pass


if __name__ == '__main__':
  unittest.main()
