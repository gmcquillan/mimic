#!/usr/bin/python2.4
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

from distutils.core import setup

setup(name='mimic',
      version='0.0.1',
      py_modules=['mimic', 'stubout'],
      url='http://code.google.com/p/pymox/',
      maintainer='Gavin McQuillan',
      maintainer_email='gavin dot mcquillan at {gmail.com}',
      license='Apache License, Version 2.0',
      description='Mock object framework',
      long_description='''Mimic is based on Mox, a mock object framework
for Python based (in turn) on the Java mock object framework EasyMock.''',
      )
