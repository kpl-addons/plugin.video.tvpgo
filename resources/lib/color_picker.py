#!/usr/bin/env python
from __future__ import division

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os
import math

import colorsys
import textwrap

from xml.etree import ElementTree
version = int(xbmc.__version__.replace('.', ''))

addon = xbmcaddon.Addon()

addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))

def get_hsv(value):
    hexrgb, name = value

    hexrgb = hexrgb.lstrip("#")
    lh = len(hexrgb)
    # Allow short and long hex codes
    r, g, b = tuple(int(i, 16) for i in textwrap.wrap(hexrgb, 3))
    return colorsys.rgb_to_hsv(r, g, b), name

def step (value, repetitions=1):
    hexrgb, name = value
    r,g,b = tuple(int(i, 16) for i in textwrap.wrap(hexrgb, 3))
    lum = math.sqrt( .241 * r + .691 * g + .068 * b )
    h, s, v = colorsys.rgb_to_hsv(r,g,b)
    h2 = int(h * repetitions)
    lum2 = int(lum * repetitions)
    v2 = int(v * repetitions)
    if h2 % 2 == 1:
        v2 = repetitions - v2
        lum = repetitions - lum
    return (h2, lum, v2), name

class ColorPicker(object):
    def __init__(self):
        dialog = xbmcgui.Dialog()

        listitems = []

        with open(os.path.join(addon.getAddonInfo('path'), 'resources', 'lib', 'colors.xml'), 'rb') as f:
            tree = ElementTree.parse(f)
        
        root = tree.getroot()

        colors = [i.text for i in root]
        names = [i.attrib['name'] for i in root]
        
        color_dict = dict(zip(colors, names))
        sort_orders = sorted(color_dict.items(), key=get_hsv)

        if version > 300:
            for name, color in sort_orders:
                listitem = xbmcgui.ListItem(color, name)
                listitems.append(listitem)

            value = dialog.colorpicker("Select color", "ffffffff", colorlist=listitems)
        else:
            for name, color in sort_orders:
                listitem = xbmcgui.ListItem(name, color)

                img =  os.path.join(addon_path, 'resources', 'lib', 'colors', '{0}.jpg'.format(color))

                listitem.setArt({'thumb': img})
                listitems.append(listitem)

            res = value = dialog.select("Select color", listitems, useDetails=True)
            if res >= 0:
                value = colors[res]
            else:
                return

        if value:
            addon.setSetting('tvpgo_color', value)
