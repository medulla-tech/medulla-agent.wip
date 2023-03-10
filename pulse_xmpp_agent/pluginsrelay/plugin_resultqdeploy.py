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

# * file pluginsrelay/plugin_resultqdeploy.py
import logging
import traceback
logger = logging.getLogger()

DEBUGPULSEPLUGIN = 25
plugin = { "VERSION" : "1.0", "NAME" : "resultqdeploy", "TYPE" : "relayserver" }

def action( objectxmpp, action, sessionid, data, message, dataerreur):
    logging.getLogger().debug("###################################################")
    logging.getLogger().debug("call %s from %s"%(plugin,message['from']))
    logging.getLogger().debug("###################################################")
    # plugin recuperation des slots sur error
    strjidagent = str(objectxmpp.boundjid.bare)
    try:
        objectxmpp.mutex.acquire(1)
        try:
            try:
                del objectxmpp.concurrentquickdeployments[sessionid]
            except KeyError:
                logger.debug("Session %s missing"%sessionid)
            logger.debug("Deleting session id %s"%sessionid)
            objectxmpp.xmpplog( "Acknowledging deployment message\nFreeing quick deployment resource %s on error\n" \
                                "Resource status: %s/%s"%(sessionid,
                                                            len(objectxmpp.concurrentquickdeployments),
                                                            objectxmpp.config.nbconcurrentquickdeployments),
                                type = 'deploy',
                                sessionname = sessionid,
                                priority = -1,
                                action = "xmpplog",
                                who = strjidagent,
                                module = "Deployment | Qdeploy | Notify",
                                date = None ,
                                fromuser = "")
        except KeyError:
            logger.error("\n%s"%(traceback.format_exc()))
            pass
    finally:
        objectxmpp.mutex.release()
