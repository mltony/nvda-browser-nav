#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import config
def getConfig(key):
    value = config.conf["browsernav"][key]
    return value

def setConfig(key, value):
    config.conf["browsernav"][key] = value
