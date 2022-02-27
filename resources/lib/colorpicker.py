import xbmcgui

import re
from typing import Union, List, Dict
from collections.abc import Mapping
from collections import namedtuple
from libka import PathArg
from libka.logs import log
from libka.format import safefmt


#: Info hot to parse combined and extra-styled setting value.
StyleParsing = namedtuple('StyleParsing', 'skin format regex')


# TODO: Move to libka.gui.colorpicker
class StylePicker:
    """Style-picker (color-picker + bold + italic) dialog for selected setting."""

    DEFAULT_ENABLED = {'color', 'bold', 'italic'}

    # TODO: Move to xml or json file
    COLORS = ['ffffe4e1', 'fffa8072', 'ffff7f50', 'ffffc3a0', 'ffcbbeb5', 'ffffdab9', 'fffaebd7', 'ffffa500',
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

    RE_COLOR_CLEAR = re.compile(r'\[(\w+).*?/\1\]\s*')
    RE_STYLE_CLEAR = re.compile(r'\[/?(\w+).*?\]\s*')
    RE_SPLIT_VALUES = re.compile(r'\s*[\s,;|+]\s*')

    STYLE_FORMATTER = {
        'color':  '[COLOR {value}][B]o[/B][/COLOR] {value}',
        'bold':   '{"B" if value == "true" else ""}',
        'italic': '{"I" if value == "true" else ""}',
    }

    STYLE_PARSER = {
        # style_name:  StyleParsing( skin_value, label_formating_value, match_regex )
        'color':  StyleParsing(r'\2', r'COLOR \2', re.compile(
            r'^(?:\[(\w+).*?/\1\]\s*)?(?:\[/?\w+.*?\]\s*)?([0-9a-f]{6}(?:[0-9a-f]{2})?)(?:\s*\[/?\w+.*?\]\s*)?',
            re.IGNORECASE)),
        'bold':   StyleParsing('true', 'B', re.compile(r'(?:\[/?(\w+).*?\]\s*)?(B)(?:\s*\[/?(\w+).*?\]\s*)?')),
        'italic': StyleParsing('true', 'I', re.compile(r'(?:\[/?(\w+).*?\]\s*)?(I)(?:\s*\[/?(\w+).*?\]\s*)?')),
    }

    def __init__(self, *, addon):
        self.addon = addon
        self.style = []
        self.color = 'ffffffff'

    def tiles(self):
        """Generate list of color tile items."""
        with self.addon.directory() as kdir:
            for color in self.COLORS:
                li = xbmcgui.ListItem(color)
                li.setArt({'icon': f'colors/{color}.png'})
                kdir.add(li, None)

    @classmethod
    def color_value(cls, color):
        return cls.RE_STYLE_CLEAR.sub('', color or '') or 'ffffffff'

    @classmethod
    def style_parse(self, value: str) -> List[str]:
        """Parse combined and extra-styled settings value to list of label-formatting styles."""
        if not isinstance(value, str):
            return value
        return [parser.regex.sub(parser.format, val.strip())
                for val in self.RE_SPLIT_VALUES.split(value)
                for name, parser in self.STYLE_PARSER.items()
                if parser.regex.fullmatch(val.strip())]

    def _parse(self, value: str) -> Dict[str, str]:
        """Parse combined and extra-styled settings value to dict of styles."""
        if isinstance(value, Mapping):
            return value
        out = {}
        for val in self.RE_SPLIT_VALUES.split(value):
            for name, parser in self.STYLE_PARSER.items():
                match = parser.regex.fullmatch(val.strip())
                if match:
                    out[name] = parser.regex.sub(parser.skin, val.strip())
        return out

    def show(self, name: PathArg[str], default: PathArg[Union[str, Dict[str, str]]] = 'ffffffff',
             *, enabled: Union[str, List[str]] = None) -> None:
        """Show dialog and save `name` setting."""
        log(f'show(name={name!r}, default={default!r}, enabled={enabled!r})', title='PICKER')
        self._parse('[COLOR ffffe4e1][B]o[/B][/COLOR] ffffe4e1, B, I')
        # parse what style is enabled
        if enabled is None:
            enabled = self.DEFAULT_ENABLED
        elif isinstance(enabled, str):
            enabled = {s.strip().lower() for s in self.RE_SPLIT_VALUES.split(enabled)}
        else:
            enabled = {enabled}
        enabled &= set(self.STYLE_FORMATTER)
        log(f'enabled={enabled!r}', title='PICKER')

        dialog = xbmcgui.WindowXMLDialog('Custom_ColorPicker_1199.xml', self.addon.info('path'),
                                         'default', '1080i')
        # enable what is enabled
        for elem in enabled:
            dialog.setProperty(f'enabled_{elem}', 'true')
        # read current and default style values
        # [1] data = self.addon.user_data.get(['libka', 'style', 'picker', name], {})
        # [1] color = self.get(name, data.get('color'))
        # TODO: get default value from xml, need custom XML settings parser
        style = self.addon.settings.get_string(name, default)
        for elem, value in self._parse(default).items():
            dialog.setProperty(f'default_{elem}', value)
        for elem, value in self._parse(style).items():
            dialog.setProperty(f'choosen_{elem}', value)
            if elem == 'color':  # why???
                dialog.setProperty('current_color', value)

        # TODO set current bold and italic buttons state

        # modal dialog
        dialog.doModal()

        # read style values
        new = {elem: dialog.getProperty(f'choosen_{elem}') for elem in self.STYLE_FORMATTER if elem in enabled}
        log(f'picked style: {new!r} ...')
        # extra-stylize style values to set settign
        value = ', '.join(v for elem, value in new.items()
                          if (v := safefmt(self.STYLE_FORMATTER[elem], value=value)))
        log(f'picked style: {new!r} -> {value!r}')
        # [1] self.addon.user_data.set(['libka', 'style', 'picker', name], {'color': color})
        # [1] self.addon.user_data.save()  # TODO: move to libka.Addon.run
        self.addon.settings.set_string(name, value)

    # [1] – Version remember last picked color even in settings not applays


class ColorPicker(StylePicker):
    """Color-picker dialog for selected setting."""

    DEFAULT_ENABLED = {'color'}
