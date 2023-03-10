# -*- coding: utf-8 -*-
#
# (c) 2020 siveo, http://www.siveo.net
#
# This file is part of Pulse 2, http://www.siveo.net
#
# Pulse 2 is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Pulse 2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pulse 2; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
# file : plugin_updatecherrypy.py

import sys
import os
from distutils.version import StrictVersion
import logging
import tempfile
from lib import utils
CHERRYPYVERSION = '8.9.1'

logger = logging.getLogger()

plugin = {"VERSION": "1.1", "NAME": "updatecherrypy", "TYPE": "machine"}


def action(xmppobject, action, sessionid, data, message, dataerreur):
    logger.debug("###################################################")
    logger.debug("call %s from %s" % (plugin, message['from']))
    logger.debug("###################################################")
    try:
        # Update if version is lower
        installed_version = checkcherrypyversion()
        if StrictVersion(installed_version) < StrictVersion(CHERRYPYVERSION):
            updatecherrypy(xmppobject, installed_version)
    except Exception:
        pass


def checkcherrypyversion():
    if sys.platform.startswith('win'):
        cmd = 'reg query "hklm\\software\\microsoft\\windows\\currentversion\\uninstall\\Pulse CherryPy" /s | Find "DisplayVersion"'
        result = utils.simplecommand(cmd)
        if result['code'] == 0:
            cherrypyversion = result['result'][0].strip().split()[-1]
        else:
            # The filetree generator is not installed. We will force installation by returning
            # version 0.0
            cherrypyversion = '0.0'
    return cherrypyversion

def updatecherrypyversion(version):
    if sys.platform.startswith('win'):
        cmd = 'REG ADD "hklm\\software\\microsoft\\windows\\currentversion\\uninstall\\Pulse CherryPy" '\
                '/v "DisplayVersion" /t REG_SZ  /d "%s" /f' % CHERRYPYVERSION

        result = utils.simplecommand(cmd)
        if result['code'] == 0:
            logger.info("we successfully updated Pulse CherryPy to version %s" % CHERRYPYVERSION)

        if version == "0.0":
            cmdDisplay = 'REG ADD "hklm\\software\\microsoft\\windows\\currentversion\\uninstall\\\Pulse CherryPy" '\
                    '/v "DisplayName" /t REG_SZ  /d "Pulse CherryPy" /f'
	    utils.simplecommand(cmdDisplay)

            cmd = 'REG ADD "hklm\\software\\microsoft\\windows\\currentversion\\uninstall\\\Pulse CherryPy" '\
                    '/v "Publisher" /t REG_SZ  /d "SIVEO" /f'

            utils.simplecommand(cmd)

def updatecherrypy(xmppobject, installed_version):
    logger.info("Updating CherryPy to version %s" % CHERRYPYVERSION)

    if sys.platform.startswith('win'):
        windows_tempdir = os.path.join("c:\\", "Windows", "Temp")
        install_tempdir = tempfile.mkdtemp(dir=windows_tempdir)
        cherrypy_filename = 'CherryPy-%s-py2.py3-none-any.whl' % CHERRYPYVERSION
        python_modules = [ 'Routes-2.4.1-py2.py3-none-any.whl',
			   'repoze.lru-0.7-py3-none-any.whl',
                           'WebOb-1.8.5-py2.py3-none-any.whl',
                           'pypiwin32-219-cp27-none-win_amd64.whl',
			   'six-1.10.0-py2.py3-none-any.whl']

        for module_to_dl in python_modules:
            dl_url = 'http://%s/downloads/win/downloads/python_modules/%s' % (
                xmppobject.config.Server, module_to_dl)
            logger.debug("Downloading %s" % dl_url)
            result, txtmsg = utils.downloadfile(dl_url, os.path.join(install_tempdir, module_to_dl)).downloadurl()

	dl_url = 'http://%s/downloads/win/downloads/python_modules/%s' % (
                xmppobject.config.Server, cherrypy_filename)
        logger.debug("Downloading %s" % dl_url)
        result, txtmsg = utils.downloadfile(dl_url, os.path.join(install_tempdir, cherrypy_filename)).downloadurl()

        if result:
            cmd = "C:\Python27\Scripts\pip install --quiet --upgrade --no-index --find-links=\"%s\" CherryPy-%s-py2.py3-none-any.whl" % (install_tempdir, CHERRYPYVERSION)
	    os.chdir(install_tempdir)
            utils.simplecommand(cmd)

            updatecherrypyversion(installed_version)
        else:
            # Download error
            logger.error("%s" % txtmsg)

