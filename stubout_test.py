#!/usr/bin/env python
#
# Unit tests for stubout.
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

import unittest

import mimic
import stubout
import stubout_testee


class StubOutForTestingTest(unittest.TestCase):
  def setUp(self):
    self.mimic = mimic.Mimic()
    self.sample_function_backup = stubout_testee.SampleFunction

  def tearDown(self):
    stubout_testee.SampleFunction = self.sample_function_backup

  def testSmartSetOnModule(self):
    mock_function = self.mimic.CreateMockAnything()
    mock_function()

    stubber = stubout.StubOutForTesting()
    stubber.SmartSet(stubout_testee, 'SampleFunction', mock_function)

    self.mimic.ReplayAll()

    stubout_testee.SampleFunction()

    self.mimic.VerifyAll()


if __name__ == '__main__':
  unittest.main()
