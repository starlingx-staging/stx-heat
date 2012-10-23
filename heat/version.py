# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

try:
    import git
except ImportError:
    git = None

try:
    from heat.vcsversion import version_info
except ImportError:
    version_info = {}

HEAT_VERSION = '8'
FINAL = False   # This becomes true at Release Candidate time


def get_git_sha():
    if not git:
        return version_info.get('sha', '')

    try:
        repo = git.Repo('.')
    except git.InvalidGitRepositoryError:
        return version_info.get('sha', '')
    return repo.head.commit.hexsha


def write_git_sha():

    sha = get_git_sha()
    vcsversion_path = 'heat/vcsversion.py'

    if sha:
        with open(vcsversion_path, 'w') as version_file:
            version_file.write("""
# This file is automatically generated by heat's setup.py, so don't edit it. :)
version_info = {
    'sha': '%s'
}
""" % (sha))
    else:
        try:
            os.remove(vcsversion_path)
        except OSError:
            pass


def version_string(type='short'):
    version = HEAT_VERSION
    if not FINAL:
        version += '-dev ' + get_git_sha()
    elif type != 'short':
        version += ' ' + get_git_sha()
    return version
