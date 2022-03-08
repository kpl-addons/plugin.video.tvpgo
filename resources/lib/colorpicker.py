import xbmcgui

from libka import PathArg


# TODO: Move to libka.gui.colorpicker
class ColorPicker:
    """Color-picker dialog for selected setting."""

    # TODO: Move to xml or json file
    colors = ['ffffe4e1', 'fffa8072', 'ffff7f50', 'ffffc3a0', 'ffcbbeb5', 'ffffdab9', 'fffaebd7', 'ffffa500',
              'ffdaa520', 'ffffd700', 'fffff68f', 'fff5f5dc', 'ffffff66', 'ffffff00', 'ffccff00', 'ffbada55',
              'ffa0db8e', 'ffd3ffce', 'ffb4eeb4', 'ff008000', 'ff00ff00', 'ffb6fcd5', 'ff00ff7f', 'ff065535',
              'ff66cdaa', 'ff7fffd4', 'ff40e0d0', 'ff81d8d0', 'ff20b2aa', 'ffafeeee', 'ff66cccc', 'ff008080',
              'ff00ffff', 'ff00ced1', 'ff133337', 'ffb0e0e6', 'ff088da5', 'ff2acaea', 'ff468499', 'ff0a75ad',
              'ffc0d6e4', 'ff0e2f44', 'ff6897bb', 'fff0f8ff', 'ff3399ff', 'ff003366', 'ffc6e2ff', 'ffe6e6fa',
              'ff000080', 'ff0000ff', 'ff8a2be2', 'ff660066', 'ff800080', 'ffff00ff', 'ffff80ed', 'ffff1493',
              'ff420420', 'ffffc0cb', 'ffffb6c1', 'fff6546a', 'ff794044', 'ff000000', 'ff101010', 'ff333333',
              'ff666666', 'ff696969', 'ff808080', 'ff999999', 'ffc0c0c0', 'ffcccccc', 'ffdddddd', 'ffeeeeee',
              'fff5f5f5', 'ffffffff', 'ffc39797', 'fff08080', 'ffff7373', 'ffff6666', 'ffff4040', 'ff800000',
              'ff8b0000', 'ff990000', 'ffcc0000', 'ffff0000']

    def __init__(self, *, addon):
        self.addon = addon

    def tiles(self):
        """Generate list of color tile items."""
        with self.addon.directory() as kdir:
            for color in self.colors:
                li = xbmcgui.ListItem(color)
                li.setLabel(color)
                li.setArt({'icon': f'colors/{color}.png'})
                kdir.add(li, None)

    def show(self, name: PathArg):
        """Show dialog and save `name` setting."""
        dialog = xbmcgui.WindowXMLDialog('Custom_ColorPicker_1199.xml', self.addon.info('path'),
                                         'default', '1080i')
        dialog.doModal()
        color = dialog.getProperty('choosen_colour')
        self.addon.settings.set_string(name, color)
