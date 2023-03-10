#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# (c) 2016-2020 siveo, http://www.siveo.net
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

import os
import os.path
import logging

logger = logging.getLogger()


class manage_fqdn_window_activedirectory:

    @staticmethod
    def basedirmachineAD():
        bd = os.path.join("/", "var", "lib", "pulse2", "organizationADmachines")
        if not os.path.isdir(bd):
            os.makedirs(bd, mode=0700)
        return bd

    @staticmethod
    def basediruserAD():
        bd = os.path.join("/", "var", "lib", "pulse2", "organizationADusers")
        if not os.path.isdir(bd):
            os.makedirs(bd, mode=0700)
        return bd

    @staticmethod
    def organizationADmachinetofile(fqdnsinfomachine):
        bd = manage_fqdn_window_activedirectory.basedirmachineAD()
        list_cn_ou_dc = fqdnsinfomachine.split("@@")

        contenuefile = list_cn_ou_dc[2]
        pathfile = os.path.join(bd, list_cn_ou_dc[1])
        if not os.path.isdir(pathfile):
            os.makedirs(pathfile, mode=0700)
        namefile = os.path.join(pathfile, list_cn_ou_dc[0])
        f = open(namefile, 'w')
        f.write(contenuefile)
        f.close()

    @staticmethod
    def organizationADusertofile(fqdnsinfomachine):
        bd = manage_fqdn_window_activedirectory.basediruserAD()
        list_cn_ou_dc = fqdnsinfomachine.split("@@")
        contenuefile = list_cn_ou_dc[2]
        pathfile = os.path.join(bd, list_cn_ou_dc[1])
        if not os.path.isdir(pathfile):
            os.makedirs(pathfile, mode=0700)
        namefile = os.path.join(pathfile, list_cn_ou_dc[0])
        f = open(namefile, 'w')
        f.write(contenuefile)
        f.close()

    @staticmethod
    def getOrganizationADmachineCN(fqdnsinfomachine):
        """
            in cas organization by machine cn is name machine
        """
        list_cn_ou_dc = fqdnsinfomachine.split("@@")
        return list_cn_ou_dc[0]

    @staticmethod
    def getOrganizationADuserCN(fqdnsinfouser):
        """
            in cas organization by user cn is name user
        """
        list_cn_ou_dc = fqdnsinfouser.split("@@")
        return list_cn_ou_dc[0]

    @staticmethod
    def getOrganizationADmachineOU(fqdnsinfomachine):
        """
            in cas organizationby machine ou is entite for machine
        """
        return fqdnsinfomachine

    @staticmethod
    def getOrganizationADuserOU(fqdnsinfouser):
        """
            in cas organization by user ou is entite for user
        """
        return fqdnsinfouser

    @staticmethod
    def getOrganizationADmachineDC(fqdnsinfomachine):
        """
            in cas organization by machine cn is domaine machine
        """
        list_cn_ou_dc = fqdnsinfomachine.split("@@")
        return list_cn_ou_dc[2]

    @staticmethod
    def getOrganizationADuserDC(fqdnsinfouser):
        """
            in cas organization by user cn is domaine user
        """
        list_cn_ou_dc = fqdnsinfouser.split("@@")
        return list_cn_ou_dc[2]
