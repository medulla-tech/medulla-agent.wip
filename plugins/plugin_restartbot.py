/**
 * (c) 2016 Siveo, http://http://www.siveo.net
 *
 * $Id$
 *
 * This file is part of Pulse .
 *
 * Pulse is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * Pulse is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Pulse.  If not, see <http://www.gnu.org/licenses/>.
 */
 
import base64
import json
import subprocess


plugin={"VERSION": "1.0", "NAME" :"restartbot"}

def action( objetxmpp, action, sessionid, data, message, dataerreur ):
    print 'plugin restartbot'
    reponse={}
    if action == 'restartbot':
        resultaction = "result%s"%action
        reponse['action'] = resultaction
        reponse['sessionid'] = sessionid
        reponse['base64'] = False
        reponse['ret'] = 0
        reponse['data'] = {}
        reponse['data']['msg']="restart %s"%message['to']
        objetxmpp.send_message( mto=message['from'],
                                mbody=json.dumps(reponse),
                                mtype='groupchat')
        objetxmpp.restartBot()
