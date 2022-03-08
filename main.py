#   GNU General Public License

#   TVP GO KODI Addon
#   Copyright (C) 2022 Kodi-PL
#   Copyright (C) 2022 Mariusz89B
#   Copyright (C) 2022 mtr81
#   Copyright (C) 2022 m1992

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see https://www.gnu.org/licenses.

#   MIT License

#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:

#   The above copyright notice and this permission notice shall be included in all
#   copies or substantial portions of the Software.

#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#   SOFTWARE.

import xbmcgui
import xbmcplugin
import xbmcvfs
import re
import json
from datetime import datetime, timedelta
from collections import namedtuple
from urllib import parse as urllib_parse

from resources.lib.colorpicker import ColorPicker
from libka import SimplePlugin, call, L, PathArg, search
from libka.logs import log
from libka.format import safefmt
from libka.deco import repeat_call

#: Channel general info
ChannelInfo = namedtuple('ChannelInfo', 'id code name title descr time_delta img',
                         defaults=(None, None, None, None))

#: Singe EPG info
EpgInfo = namedtuple('EpgInfo', 'id code live start end duration title year land desc desc_long img',
                     defaults=('', '', '', '', '', '', '', '', '', ''))
EpgInfo.dt_start = property(lambda self: datetime.fromtimestamp(self.start / 1000))
EpgInfo.dt_end = property(lambda self: datetime.fromtimestamp(self.end / 1000))
EpgInfo.time_range = property(lambda self: f'{self.dt_start:%H:%M} - {self.dt_end:%H:%M}')

sport_tvp_base_url = 'https://sport.tvp.pl/api/tvp-stream'


class RepeatException(Exception):
    pass


class Main(SimplePlugin):

    def __init__(self):
        def stylize(name, defcolor='ffffffff'):
            colname = f'tvpgo_{name}_color'
            styles = [f'COLOR {self.settings.get(colname) or defcolor}']
            if self.settings.get(f'tvpgo_{name}_style_bold'):
                styles.append('B')
            return styles

        super().__init__()
        self.styles = {
            'channel': stylize('channel', 'ffffffff'),
            'time': stylize('time', '80ffffff'),
        }
        if self.settings.tvpgo_format == 0:
            self.title_format: str = '{channel} {time} - {title}'
        else:
            self.title_format: str = '{channel} {title} - {time}'

        self.thumb = self.media.image('landscape.png')
        self.poster = self.media.image('poster.png')
        self.banner = self.media.image('banner.png')
        self.icon = self.resources.base / 'icon.png'
        self.fanart = self.resources.base / 'fanart.png'
        now = datetime.now()
        self.tz_offset = now - datetime.utcfromtimestamp(now.timestamp())
        self.colorpicker = ColorPicker(addon=self)
        self.search_collected = list()

    def style(self, text, name):
        """Style `text` by `name` rules."""
        return self.format_title(text, style=self.styles[name])

    def home(self):
        # default art
        art = {'thumb': self.thumb, 'poster': self.poster, 'banner': self.banner,
               'icon': self.icon, 'fanart': self.fanart}
        with self.directory() as kdir:
            kdir.menu('Kanały na żywo', self.live, art=art)
            kdir.menu('Archiwum', self.replay, art=art)
            kdir.menu('VOD', self.vod, art=art)

    # HACK, "@staticmethod" will be removed after move repeat_call to libka
    @staticmethod
    def _fail_notification():
        xbmcgui.Dialog().notification(L(30027, '[B]Error[/B]'),
                                      L(30028, 'Connection to the service has failed'),
                                      xbmcgui.NOTIFICATION_INFO, 6000, False)

    def get_epgs(self, *, all_day=False, tv_code=None):
        headers = {
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.56',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3;q=0.9',
            'Referer': 'https://www.tvp.pl/program-tv',
            'Accept-Language': 'sv,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,pl;q=0.6,fr;q=0.5',
        }
        url = 'https://www.tvp.pl/program-tv'
        response = self.get(url, headers=headers).text
        stations_regex = re.compile(r'window.__stationsProgram\[\d+]\s=\s(.*?)</script>',
                                    re.MULTILINE | re.DOTALL)

        epg_data = []
        for match in stations_regex.finditer(response):
            js_data = re.sub(r'},\n}', r'}\n}', match.group(1)).replace(';', '')

            data = json.loads(js_data)
            # XXX DEBUG
            # if data['station']['name'] == 'TVP1':
            #     with open('/tmp/epg1.json', 'w') as f:
            #         json.dump(data, f)
            if tv_code is None or tv_code == data.get('station', {}).get('code'):
                for e in data['items']:
                    start = e.get('date_start')
                    end = e.get('date_end')
                    now_msec = datetime.now().timestamp() * 1000
                    if all_day or start <= now_msec <= end:
                        ch_id = e.get('_id')
                        ch_code = e.get('station_code')
                        p_live = 'Live' if e.get('live') else ''
                        prog = e.get('program')
                        if prog is not None:
                            imgs = prog.get('akpa_images')
                            if imgs is not None:
                                for img in imgs:
                                    img_id = img['fileName'].replace('.jpg', '')
                                    p_img = f'https://s2.tvp.pl/images-akpa/0/0/0/uid_' \
                                            f'{img_id}_width_1280_play_0_pos_0_gs_0_height_720.jpg '
                            else:
                                p_img = ''
                            epg_data.append(EpgInfo(ch_id, ch_code, p_live, start, end, e.get('duration'),
                                                    prog['title'], prog['year'], prog['land'], prog['description'],
                                                    prog['description_long'], p_img))

        return epg_data

    @repeat_call(5, 1, RepeatException, on_fail=_fail_notification)
    def channel_array_gen(self):
        url = "https://tvpstream.tvp.pl/api/tvp-stream/program-tv/stations"
        response = self.jget(url)
        try:
            ch_data = response['data']
        except Exception:
            raise RepeatException()

        ar_chan = []
        re_name = re.compile(r'^(?:EPG)?\s*([^\d]+?)\s*(\d.*)?\s*$')
        for c in ch_data:
            ch_id = c['id']
            ch_code = c['code']
            ch_name = ' '.join(s for s in re_name.search(c['name']).groups() if s)
            ch_img = safefmt(c['image_square']['url'], width=500, height=500)

            ar_chan.append(ChannelInfo(code=ch_code, name=ch_name, img=ch_img, id=ch_id))

        if self.settings.tvpgo_sort == 1:
            ar_chan = sorted(ar_chan, key=lambda x: x.name)

        return ar_chan

    def live(self):
        channels = self.channel_array_gen()
        epg_data = {epg.code: epg for epg in self.get_epgs()}

        with self.directory() as kdir:
            for ch in channels:
                channel = self.style(ch.name, 'channel')
                epg = epg_data.get(ch.code)
                if epg:
                    if epg.start and epg.end:
                        dt_start = datetime.fromtimestamp(int(epg.start) / 1000)
                        dt_end = datetime.fromtimestamp(int(epg.end) / 1000)

                        if epg.title:
                            time_delta = self.style(f'[{dt_start:%H:%M} - {dt_end:%H:%M}]', 'time')
                            title = self.title_format.format(channel=channel, title=epg.title, time=time_delta)
                        else:
                            title = channel
                    else:
                        title = channel

                    thumb = ch.img or self.thumb
                    poster = epg.img or self.poster
                    art = ({'thumb': thumb, 'poster': poster, 'banner': self.banner,
                            'icon': self.icon, 'fanart': self.fanart})
                    kdir.play(title, call(self.play_channel, code=ch.code, ch_id=ch.id), art=art,
                              info={'title': title, 'sorttitle': title, 'tvshowtitle': title, 'status': epg.live,
                                    'year': epg.year, 'plotoutline': epg.desc,
                                    'plot': epg.desc_long, 'duration': epg.duration},
                              menu=[
                                  (L(30039, 'Program'), self.cmd.Container.Update(self.program, epg.code)),
                              ])
                else:
                    title = channel
                    thumb = ch.img or self.thumb
                    art = ({'thumb': thumb, 'poster': self.poster, 'banner': self.banner,
                            'icon': self.icon, 'fanart': self.fanart})
                    kdir.play(title, call(self.play_channel, code=ch.code, ch_id=ch.id), art=art)

    def nop(self):
        """No-Operation."""

    def program(self, code=None):  # HACK, without None exception raises. TODO: investigate it.
        """List EPG for given program."""
        with self.directory() as kdir:
            now_msec = datetime.now().timestamp() * 1000
            for epg in self.get_epgs(all_day=True, tv_code=code):
                time = self.style(f'[{epg.time_range}]', epg.time_range)
                title = f'{time} – {epg.title}'
                if epg.start > now_msec:
                    kdir.item(title, self.nop)
                else:
                    thumb = epg.img or self.thumb
                    poster = epg.img or self.poster
                    art = ({'thumb': thumb, 'poster': poster, 'banner': self.banner,
                            'icon': self.icon, 'fanart': self.fanart})
                    info = {'title': title, 'sorttitle': title, 'tvshowtitle': title, 'status': epg.live,
                            'year': epg.year, 'plotoutline': epg.desc, 'plot': epg.desc_long, 'duration': epg.duration}
                    if epg.end < now_msec:
                        kdir.play(title, call(self.play_programme, code=epg.code, prog_id=epg.id), info=info, art=art)
                    else:
                        kdir.play(title, call(self.play_channel, code=epg.code), art=art, info=info)

    @repeat_call(5, 1, RepeatException, on_fail=_fail_notification)
    def play_channel(self, code, ch_id=None):
        streams = ''
        url = f'https://tvpstream.tvp.pl/api/tvp-stream/stream/data?station_code={code}'
        response = self.jget(url)
        try:
            live = response['data']
            if live:
                urls = live['stream_url']
                response = self.jget(urls)
                streams = response['formats']
        except Exception:
            raise RepeatException() from None

        url_stream = self.get_stream_of_type(streams)['url']
        protocol_type = self.get_stream_of_type(streams)['protocol']
        stream_mime_type = self.get_stream_of_type(streams)['mime_type']
        url_stream = self.apply_timeshift(url_stream)
        self.play(url_stream, protocol_type, stream_mime_type)

    @repeat_call(5, 1, RepeatException, on_fail=_fail_notification)
    def replay_channels_array_gen(self):
        url = f'https://tvpstream.tvp.pl/api/tvp-stream/program-tv/stations'
        response = self.jget(url)
        if 'data' not in response:
            raise RepeatException()

        ar_chan = []
        for c in response['data']:
            ch_code = c['code']
            ch_name = c['name'].replace('EPG - ', '')

            ch_name = re.sub(r"([0-9]+(\.[0-9]+)?)", r" \1", ch_name).strip().replace('  ', ' ')

            ch_id = c['id']
            ch_img = c['image_square']['url'].replace('{width}', '500').replace('{height}', '500')

            ar_chan.append(ChannelInfo(code=ch_code, name=ch_name, img=ch_img, id=ch_id))

        if self.settings.tvpgo_sort == 1:
            ar_chan = sorted(ar_chan, key=lambda x: x.name)

        return ar_chan

    def replay(self):
        with self.directory() as kdir:
            for ch in self.replay_channels_array_gen():
                set_info = {'title': ch.name, 'sorttitle': ch.name, 'plot': ''}
                thumb = ch.img or self.thumb
                poster = ch.img or self.poster
                kdir.menu(ch[1], call(self.replay_calendar_gen, ch_code=ch.code, ch_image=ch.img),
                          art={'thumb': thumb, 'poster': poster, 'banner': self.banner,
                               'icon': self.icon, 'fanart': self.fanart},
                          info=set_info)

    def replay_calendar_gen(self, ch_code, ch_image):
        now = datetime.now()
        ar_date = [f'{now - timedelta(days=n):%Y-%m-%d}' for n in range(7)]
        with self.directory() as kdir:
            for date in ar_date:
                kdir.menu(date, call(self.replay_programs_gen, ch_code=ch_code, ch_img=ch_image, date=date),
                          info={'title': date, 'sorttitle': date, 'plot': ''},
                          art={'thumb': ch_image, 'poster': ch_image, 'banner': self.banner, 'icon': self.icon,
                               'fanart': self.fanart})

    @repeat_call(5, 1, RepeatException, on_fail=_fail_notification)
    def replay_programs_array_gen(self, ch_code, date, retry=0):
        def hm(t):
            return f'{datetime.fromtimestamp(t / 1000):%H:%S}'

        url = f'https://tvpstream.tvp.pl/api/tvp-stream/program-tv/index?station_code={ch_code}&date={date}'
        response = self.jget(url)
        if 'data' not in response:
            raise RepeatException()
        ar_prog = []
        now_msec = int(datetime.now().timestamp() * 1000)  # TODO handle timezone

        for p in response['data']:
            if p['date_start'] < now_msec:
                p_id = p['record_id']
                ch_code = p['station_code']

                ch_name = p['station']['name'].replace('EPG - ', '')
                ch_name = re.sub(r"([0-9]+(\.[0-9]+)?)", r" \1", ch_name).strip().replace('  ', ' ')

                p_title = p['title']
                p_desc = p['description']
                p_time_delta = self.style(f'[{hm(p["date_start"])} - {hm(p["date_end"])}]', 'time')
                p_logo = ''
                program = p.get('program')
                if program is not None:
                    cycle = program.get('cycle')
                    if cycle is not None:
                        logo = cycle['image_logo']
                        if logo:
                            p_logo = safefmt(logo['url'], width=360, height=205)

                ar_prog.append(ChannelInfo(p_id, ch_code, ch_name, p_title, p_desc, p_time_delta, p_logo))

        return ar_prog

    def replay_programs_gen(self, ch_code, ch_img, date):
        with self.directory() as kdir:
            for p in self.replay_programs_array_gen(ch_code, date):
                channel = self.style(p.name, 'channel')
                title = self.title_format.format(channel=channel, title=p.title, time=p.time_delta)
                art = {'thumb': p.img or ch_img, 'poster': p.img or ch_img, 'banner': self.banner,
                       'icon': self.icon, 'fanart': self.fanart}

                kdir.play(title, call(self.play_programme, code=ch_code, prog_id=p.id),
                          info={'title': title, 'sorttitle': p.title, 'plot': p.descr}, art=art)

    @repeat_call(5, 1, RepeatException, on_fail=_fail_notification)
    def get_replay_program_streams(self, ch_code, prog_id, retry=0):
        retry += 1

        url = f'https://tvpstream.tvp.pl/api/tvp-stream/stream/data?station_code={ch_code}&record_id={prog_id}'

        response = self.jget(url)
        if 'data' not in response:
            raise RepeatException()

        urls = response['data']['stream_url']
        response = self.jget(urls)
        streams = response['formats']

        return streams

    def vod(self):
        response = self.jget(f'{sport_tvp_base_url}/block/list?device=android')
        with self.directory() as kdir:
            for item in response['data']:
                kdir.menu(item['title'], call(self.vod_category, item['_id']))
            kdir.menu('SZUKAJ', self.search)

    def vod_category(self, cid: PathArg[int]):
        response = self.jget(f'{sport_tvp_base_url}/block/list?device=android')
        for category in response['data']:
            if category['_id'] == cid:
                with self.directory() as kdir:
                    for item in category['items']:
                        kdir.play(item['title'],
                                  call(self.vod_play, station_code=item["station_code"], record_id=item["record_id"]))
                # found category, ignore rest
                break

    def vod_play(self, station_code, record_id):
        url = f'{sport_tvp_base_url}/stream/data'
        response = self.jget(url, params={'station_code': station_code, 'record_id': record_id, 'device': 'android'})
        return self.sort_vod_streams(response)

    def sort_vod_streams(self, url):
        response = self.jget(url["data"]["stream_url"])
        play_item_url = self.get_stream_of_type(response['formats'])['url']
        protocol = self.get_stream_of_type(response['formats'])['protocol']
        self.play(play_item_url, drm_protocol=protocol)

    def play(self, url_stream, drm_protocol, drm_mime_type=None):
        from inputstreamhelper import Helper  # pylint: disable=import-outside-toplevel

        is_helper = Helper(drm_protocol)
        if is_helper.check_inputstream():
            play_item = xbmcgui.ListItem(path=url_stream)
            if drm_mime_type is not None:
                play_item.setMimeType(drm_mime_type)
            play_item.setContentLookup(False)
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
            play_item.setProperty("IsPlayable", "true")
            play_item.setProperty('inputstream.adaptive.manifest_type', drm_protocol)
            xbmcplugin.setResolvedUrl(handle=self.handle, succeeded=True, listitem=play_item)

    def play_programme(self, code, prog_id):
        streams = self.get_replay_program_streams(code, prog_id)
        url_stream = self.get_stream_of_type(streams)['url']
        protocol_type = self.get_stream_of_type(streams)['protocol']
        stream_mime_type = self.get_stream_of_type(streams)['mime_type']
        self.play(url_stream=url_stream, drm_protocol=protocol_type, drm_mime_type=stream_mime_type)

    def apply_timeshift(self, url_stream, keep_begin_time=True):
        if url_stream is not None:
            time_delta = self.settings.tvpgo_timeshift_delta_value
            if self.settings.tvpgo_timeshift_type == 1 and 0 < time_delta <= 10080:
                url_stream = self.adjust_timeshift_args(url_stream,
                                                        begin_time=self.gen_begin_time_from_timedelta(time_delta))
            else:
                url_stream = self.adjust_timeshift_args(url_stream, keep_begin_time=keep_begin_time)

            return url_stream

    # Searching ...
    def get_search_results(self, query, index):
        list_queries = [
            {
                'query': query,
                'scope': 'bestresults',
                'limit': 20,
                'page': 1,
                'device': 'android'
            },
            {
                'query': query,
                'scope': 'programtv',
                'limit': 20,
                'page': 1,
                'device': 'android'
            },
            {
                'query': query,
                'scope': 'vodprogrammesandepisodes',
                'limit': 20,
                'page': 1,
                'device': 'android'
            },
            {
                'query': query,
                'scope': 'vodepisodes',
                'limit': 20,
                'page': 1,
                'device': 'android'
            }
        ]
        if index < 4:
            response = self.jget(f'{sport_tvp_base_url}/search?', params=list_queries[index])
            if response['data']:
                self.search_collected.append(response['data']['occurrenceitem'])
                index += 1
                return self.get_search_results(query, index)
        else:
            return self.list_occurrenceitems(self.search_collected)

    def list_occurrenceitems(self, data):
        filtered_data = {item['title']: item for results in data for item in results}
        with self.directory() as kdir:
            for item in filtered_data.values():
                kdir.menu(item['title'], call(self.get_search_tabs, occurrenceid=item['id']))

    def get_search_tabs(self, occurrenceid):
        query = {
            'id': occurrenceid,
            'device': 'android'
        }
        response = self.jget(f'{sport_tvp_base_url}/program-tv/occurrence', params=query)
        with self.directory() as kdir:
            if response['data']:
                for item in response['data']['tabs']:
                    category = item.get('params').get('category')
                    people_id = item.get('params').get('id')
                    if category:
                        cat20 = category.get('20')[0]
                        cat30 = category.get('30')[0]
                        if cat20 and cat30:
                            kdir.menu(self.style(item['title'], 'channel'),
                                      call(self.list_seasons, id=occurrenceid, endpoint_type=item['endpoint_type'],
                                           cat20=cat20, cat30=cat30))
                    elif people_id:
                        kdir.menu(self.style(item['title'], 'channel'),
                                  call(self.list_seasons, id=occurrenceid, endpoint_type=item['endpoint_type'],
                                       people_id=people_id))
                    else:
                        kdir.menu(self.style(item['title'], 'channel'),
                                  call(self.list_seasons, id=occurrenceid, endpoint_type=item['endpoint_type']))
            else:
                response = self.jget(f'{sport_tvp_base_url}/program-tv/occurrence-video', params=query)
                for item in response['data']['tabs']:
                    params = item.get('params')
                    people_id = params.get('id')
                    kdir.menu(self.style(item['title'], 'channel'),
                              call(self.list_seasons, id=occurrenceid, people_id=people_id,
                                   endpoint_type=item['endpoint_type']))

    def list_seasons(self, id, endpoint_type=None, people_id=None, cat20=None, cat30=None):
        if endpoint_type == 'SEASON_VIDEOS':
            query = {
                'id': id,
                'device': 'android'
            }
            response = self.jget(f'{sport_tvp_base_url}/program-tv/occurrence-video', params=query)
            self.list_search_items(response)

        elif endpoint_type == 'OCCURRENCES':
            query = {
                'onlycatchup': 1,
                'category[20][]': cat20,
                'category[30][]': cat30,
                'include_images': 1,
                'page': 1,
                'limit': 40,
                'device': 'android'
            }
            response = self.sess.post(f'{sport_tvp_base_url}/program-tv/occurrences', params=query).json()
            self.list_search_items(response)

        elif endpoint_type == 'PEOPLES':
            query = {
                'id': people_id,
                'types[]': 30,
                'page': 1,
                'limit': 40,
                'device': 'android'
            }
            response = self.jget(f'{sport_tvp_base_url}/program-tv/program/people', params=query)
            with self.directory() as kdir:
                for item in response['data']:
                    kdir.menu(f'{self.style(item["name"], "channel")} [{item["description"]}]',
                              call(self.call_people, person_id=item['id']))

    def show_seasons(self, seasonid):
        query = {
            'id': seasonid,
            'page': 1,
            'limit': 20,
            'device': 'android'
        }
        response = self.jpost(f'{sport_tvp_base_url}/season/videos', params=query)
        with self.directory() as kdir:
            for item in response['data']:
                kdir.play(f'{self.style(item["title"], "channel")} – {item["subtitle"]}',
                          call(self.play_search_result, playid=item['id']))

    def call_people(self, person_id):
        query = {
            'personId': person_id,
            'device': 'android'
        }
        response = self.jget(f'{sport_tvp_base_url}/search/people/tabs', params=query)
        with self.directory() as kdir:
            if response['data']:
                for item in response['data']:
                    kdir.menu(item['title'], call(self.person_search, person_id=item['params']['personId'],
                                                  scope=item['params']['scope']))
            else:
                kdir.item('Brak informacji.', self.nop)

    def person_search(self, person_id, scope):
        query = {
            'scope': scope,
            'personId': person_id,
            'page': 1,
            'limit': 40,
            'device': 'android'
        }
        response = self.jget(f'{sport_tvp_base_url}/search/people', params=query)
        with self.directory() as kdir:
            for item in response['data']:
                kdir.menu(f'{self.style(item["title"], "channel")} – {item["subtitle"]}',
                          call(self.person_search_result, program_id=item['id']))

    def person_search_result(self, program_id):
        query = {
            'id': program_id,
            'device': 'android'
        }
        response = self.jget(f'{sport_tvp_base_url}/program-tv/occurrence', params=query)
        with self.directory() as kdir:
            if response['data']:
                for item in response['data']['tabs']:
                    kdir.menu(self.style(item['title'], 'channel'),
                              call(self.list_seasons, id=program_id, endpoint_type=item['endpoint_type']))

    def list_search_items(self, data):
        with self.directory() as kdir:
            retrieved_data = data.get('data')
            if type(retrieved_data) is dict:
                tabs = retrieved_data.get('tabs')
            else:
                tabs = retrieved_data[0].get('tabs')
            if tabs:
                for results in retrieved_data.get('tabs'):
                    if results.get('params').get('seasons'):
                        for item in results.get('params').get('seasons'):
                            kdir.menu(f'{self.style(item["title"], "channel")}',
                                      call(self.show_seasons, seasonid=item['id']))
            else:
                for item in retrieved_data:
                    kdir.menu(f'{self.style(item["title"], "channel")}', call(self.show_seasons, seasonid=item['id']))

    def play_search_result(self, playid):
        stream_data = self.jget(f'{sport_tvp_base_url}/stream/data?id={playid}&device=android')
        if stream_data:
            stream_url = self.jget(stream_data['data']['stream_url'])
            streams = stream_url['formats']
            url_stream = self.get_stream_of_type(streams)['url']
            protocol_type = self.get_stream_of_type(streams)['protocol']
            stream_mime_type = self.get_stream_of_type(streams)['mime_type']

            play_item = xbmcgui.ListItem(path=url_stream)
            play_item.setMimeType(stream_mime_type)
            play_item.setContentLookup(False)
            play_item.setProperty('#KODIPROP:inputstream=inputstream.adaptive', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', protocol_type)
            play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)

    @search.folder
    def searching_tvpgo(self, query):
        self.get_search_results(query=query, index=0)

    @staticmethod
    def adjust_timeshift_args(input_url, begin_time=None, keep_begin_time=True):
        input_url_parsed = urllib_parse.urlparse(input_url)
        input_params = dict(urllib_parse.parse_qsl(input_url_parsed.query))

        if not keep_begin_time:
            del input_params['begin']

        if begin_time is not None:
            input_params['begin'] = begin_time

        input_params['end'] = ''

        input_url_list = list(input_url_parsed)
        input_url_list[4] = urllib_parse.urlencode(input_params)

        return urllib_parse.urlunparse(input_url_list)

    def gen_begin_time_from_timedelta(self, delta_min):
        return f'{datetime.utcnow() - timedelta(minutes=delta_min):%Y%m%dT%H%M%S}'

    @staticmethod
    def get_stream_of_type(streams):
        sorted_data = sorted(streams, key=lambda d: list(str(d['totalBitrate'])), reverse=True)
        url_stream = sorted_data[0]['url']
        mime_type = sorted_data[0]['mimeType']
        if mime_type == 'application/dash+xml':
            return {
                'url': url_stream,
                'mime_type': mime_type,
                'protocol': 'mpd'
            }

        elif mime_type == 'application/x-mpegurl':
            return {
                'url': url_stream,
                'mime_type': mime_type,
                'protocol': 'hls'
            }

        elif mime_type == 'video/mp2t':
            return {
                'url': url_stream,
                'mime_type': mime_type,
                'protocol': 'hls'
            }

        elif mime_type == 'video/mp4':
            return {
                'url': url_stream,
                'mime_type': mime_type,
                'protocol': 'hls'
            }
        elif mime_type == 'application/vnd.ms-ss':
            return {
                'url': url_stream,
                'mime_type': mime_type,
                'protocol': 'ism'
            }

    def build_m3u(self):
        path_m3u = self.settings.tvpgo_path_m3u
        file_name = self.settings.tvpgo_filename

        if not file_name or not path_m3u:
            xbmcgui.Dialog().notification('TVP GO', L(30022, 'Set filename and destination directory'),
                                          xbmcgui.NOTIFICATION_ERROR)
            return

        xbmcgui.Dialog().notification('TVP GO', L(30025, 'Generate playlist'), xbmcgui.NOTIFICATION_INFO)
        data = '#EXTM3U\n'

        for channel in self.channel_array_gen():
            data += (f'#EXTINF:0 tvg-id="{channel.name}" tvg-logo="{channel.img}" group-title="TVPGO",{channel.name}\n'
                     f'plugin://plugin.video.tvpgo/play_channel?code={channel.code}&ch_id={channel.id}\n')

        try:
            f = xbmcvfs.File(path_m3u + file_name, 'w')
            f.write(data)
        finally:
            f.close()
        xbmcgui.Dialog().notification('TVP GO', L(30029, 'Playlist M3U generated'), xbmcgui.NOTIFICATION_INFO)


if __name__ == '__main__':
    import sys

    log.info(f'============= {sys.argv}')
    Main().run()
