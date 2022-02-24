#!/usr/bin/env python
import xbmcgui, xbmcaddon


class ColorPicker:
    # TODO: Save settings using libka
    def __init__(self):
        self.dialog = xbmcgui.WindowXMLDialog('Custom_ColorPicker_1199.xml', xbmcaddon.Addon().getAddonInfo('path'),
                                              'default', '1080i')
        self.dialog.doModal()
        self.choosen_colour = self.dialog.getProperty('choosen_colour')
        xbmcaddon.Addon().setSetting(id='tvpgo_color', value=self.choosen_colour)
