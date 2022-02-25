import xbmcgui
import xbmcaddon
import xbmcplugin
import sys

colors = ['ffff80ed', 'ff065535', 'ff000000', 'ff133337', 'ffffc0cb', 'ffffffff', 'ffffe4e1', 'ff008080', 'ffff0000',
          'ffe6e6fa', 'ffffd700', 'ffffa500', 'ff00ffff', 'ffff7373', 'ff40e0d0', 'ff0000ff', 'ffd3ffce', 'fff0f8ff',
          'ffc6e2ff', 'ffb0e0e6', 'ff666666', 'fffaebd7', 'ffbada55', 'ff003366', 'ffffb6c1', 'ffffff00', 'fffa8072',
          'ffc0c0c0', 'ff800000', 'ff7fffd4', 'ff800080', 'ffc39797', 'ffeeeeee', 'fff08080', 'ffcccccc', 'fffff68f',
          'ff00ff00', 'ff20b2aa', 'ff333333', 'ffffc3a0', 'ff66cdaa', 'ffff6666', 'ffffdab9', 'ffc0d6e4', 'ffff00ff',
          'ffff7f50', 'ffafeeee', 'ff468499', 'ffcbbeb5', 'ff008000', 'ff00ced1', 'fff6546a', 'ffb4eeb4', 'ffb6fcd5',
          'ff660066', 'ff0e2f44', 'ffdaa520', 'ff990000', 'ff696969', 'ff808080', 'fff5f5f5', 'ff6897bb', 'ff088da5',
          'ff000080', 'ff8b0000', 'fff5f5dc', 'ff101010', 'ffffff66', 'ffdddddd', 'ff8a2be2', 'ff2acaea', 'ff81d8d0',
          'ff0a75ad', 'ffff4040', 'ffccff00', 'ff66cccc', 'ff420420', 'ff00ff7f', 'ff794044', 'ffa0db8e', 'ffff1493',
          'ff3399ff', 'ffcc0000', 'ff999999']


class TilesGen:
    # TODO: Set dynamic content using libka
    def __init__(self):
        addon_handle = int(sys.argv[1])

        for color in colors:
            li = xbmcgui.ListItem(color)
            li.setLabel(color)
            li.setArt({'icon': f'colors/{color}.png'})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=None, listitem=li)

        xbmcplugin.endOfDirectory(addon_handle)


class ColorPicker:
    # TODO: Save settings using libka
    def __init__(self):
        self.dialog = xbmcgui.WindowXMLDialog('Custom_ColorPicker_1199.xml', xbmcaddon.Addon().getAddonInfo('path'),
                                              'default', '1080i')
        self.dialog.doModal()
        self.choosen_colour = self.dialog.getProperty('choosen_colour')
        xbmcaddon.Addon().setSetting(id='tvpgo_color', value=self.choosen_colour)
