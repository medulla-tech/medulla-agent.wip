#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# (c) 2016-2017 siveo, http://www.siveo.net
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
#
# fil pulse_xmpp_master_substitute/pluginsmastersubstitute/plugin_unregistrer_agent.py


from lib.plugins.xmpp import XmppMasterDatabase
import logging
import traceback
import json

logger = logging.getLogger()


plugin = {"VERSION": "1.0", "NAME": "unregistrer_agent", "TYPE" : "substitute", "FEATURE": "subscribe"}


# Ce plugin est appelé par l'agent machine.
# quand l'agent machine détecte un changement de "domaine" dans son JID.(fonction unregister_agent)
# les conséquences de ce changement de domaine sont traduites par 1 changement de serveur jabberd de agent machine.
# le compte de l'ancien jid sur l'ancien jabberd doit etre supprimé.
# les informations reçues par ce plugin sont le compte a supprimer.

# ce plugin cherche le serveur jabberd en charge de ce JID et forwardé le message au relay server associé a ce serveur jabberd.
# le relay serveur par son plugin  unregistrer_agent supprime le compte dans jabberd


def action(xmppobject, action, sessionid, data, msg, ret, dataobj):
    logger.debug("-----------------------------------------------------------------------------------------")
    logger.debug(plugin)
    logger.debug("-----------------------------------------------------------------------------------------")
    # determine ARS qui supprime le compte.

    #SELECT * FROM xmppmaster.relayserver where jid like "%@jfk-ars1/%";
    if "user" in data and "domain" in data and "resource" in data and \
        data['user'].strip() != "" and  data['domain'].strip() != "" and  data['resource'].strip() != "":
        try:
            relayserveur = XmppMasterDatabase().getRelayServerfromjiddomain(data['domain'])
            msg={ "action" : "unregistrer_agent",
                  "sessionid" : sessionid,
                  "data" : data,
                  "base64": false,
                  "ret" : 0
                }
            if relayserveur:
                xmppobject.send_message(mto=relayserveur['jid'],
                                        mbody=json.dumps(msg),
                                        mtype='chat')
            else:
                logger.error("unregistrer_agent ars domain %s missing" %data['domain'])
        except Exception, e:
            logger.error("plugin unregistrer_agent substitute error %s\n%s"%(str(e), traceback.format_exc()))
    else:
        logger.error("JId incorecte")
