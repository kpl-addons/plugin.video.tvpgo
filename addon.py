#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import os
import sys

import six
from six.moves import urllib_error, urllib_request, urllib_parse, http_cookiejar

import requests
import urllib

from libka import SimplePlugin, call

try:
    from urllib.parse import urlencode, quote_plus, quote, unquote
except ImportError:
    from urllib import urlencode, quote_plus, quote, unquote

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

import re
import json
import random
import time
import datetime

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.tvpgo')
file_name = addon.getSetting('tvpgo_filename')
path_m3u = addon.getSetting('tvpgo_path_m3u')

mode = addon.getSetting('mode')
try:
    color = int(addon.getSetting('tvpgo_color'))
except:
    color = 0
colors = ['', 'skyblue', 'dodgerblue', 'lightgreen', 'indianred', 'thistle', 'goldenrod', 'sandybrown', 'button_focus']

format_list = addon.getSetting('tvpgo_format')
if format_list == '0':
    form = 0
else:
    form = 1

quantity = addon.getSetting('tvpgo_quantity')

try:
    view = int(addon.getSetting('tvpgo_auto_view'))
except:
    view = 0
views = ['default', 'episodes', 'files', 'movies', 'tvshows', 'videos']

ordered = addon.getSetting('tvpgo_sort')
if ordered == '0':
    order = 0
else:
    order = 1

addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
strings = xbmc.getLocalizedString

thumb = os.path.join(addon_path, 'resources', 'art', 'landscape.png')
poster = os.path.join(addon_path, 'resources', 'art', 'poster.png')
banner = os.path.join(addon_path, 'resources', 'art', 'banner.png')
icon = os.path.join(addon_path, 'icon.png')
fanart = os.path.join(addon_path, 'fanart.png')
timeout = (3, 5)


class source_exception(Exception):
    pass


def build_url(query):
    return base_url + '?' + urllib_parse.urlencode(query)


def get_requests(url, data={}, headers={}, payload={}, txt=False):
    try:
        if data:
            response = requests.post(url, headers=headers, json=data)
        else:
            response = requests.get(url, headers=headers)

        if not txt:
            content = json.loads(response.text)
        else:
            content = response.text

        return content

    except:
        xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
        raise source_exception('Error loading list')


def set_view():
    if views[view] != 'default':
        xbmcplugin.setContent(addon_handle, views[view])


def get_epgs(retry=0):
    from datetime import datetime

    retry += 1

    url = 'https://www.tvp.pl/program-tv'

    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.56',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Referer': 'https://www.tvp.pl/program-tv',
        'Accept-Language': 'sv,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,pl;q=0.6,fr;q=0.5',
    }

    response = get_requests(url, headers=headers, txt=True)

    try:
        stations_regex = re.compile(r'window.__stationsProgram\[\d+\]\s=\s(.*?)</script>', re.MULTILINE | re.DOTALL)
        finds = stations_regex.findall(response)

    except:
        time.sleep(1)
        if retry < 6:
            return get_epgs(retry)
        else:
            xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
            raise source_exception('Error loading list')

    epg_data = []

    for js_data in finds:
        js_data = re.sub(r'},\n}', r'}\n}', js_data).replace(';', '')

        data = json.loads(js_data)
        for e in data['items']:
            ch_id = e.get('_id')
            ch_code = e.get('station_code')

            live = e.get('live')
            if live == 'true':
                p_live = 'Live'
            else:
                p_live = ''

            start = e.get('date_start')
            if start is not None:
                p_start = int(start)

            end = e.get('date_end')
            if end is not None:
                p_end = int(end)

            p_duration = e.get('duration')

            program = e.get('program')
            if program is not None:
                imgs = program.get('akpa_images')
                if imgs is not None:
                    for img in imgs:
                        img_id = img['fileName'].replace('.jpg', '')
                        p_img = 'https://s2.tvp.pl/images-akpa/0/0/0/uid_{id}_width_1280_play_0_pos_0_gs_0_height_720.jpg'.format(id=img_id)
                else:
                    p_img = ''

                p_title = program['title']
                p_year = program['year']
                p_land = program['land']
                p_desc = program['description']
                p_desc_long = program['description_long']

            now = int(datetime.timestamp(datetime.now())) * 1000

            if p_start <= now <= p_end:
                epg_data.append([ch_id, ch_code, p_live, p_start, p_end, p_duration, p_title, p_year, p_land, p_desc, p_desc_long, p_img])

    return epg_data


def replay_channels_array_gen(retry=0):
    retry += 1

    url = "https://tvpstream.tvp.pl/api/tvp-stream/program-tv/stations"

    response = get_requests(url)
    try:
        ch_data = response['data']
    except:
        time.sleep(1)
        if retry < 6:
            return replay_channels_array_gen(retry)
        else:
            xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
            raise source_exception('Error loading list')

    ar_chan = []

    for c in ch_data:
        ch_code = c['code']
        ch_name = c['name'].replace('EPG - ', '')

        ch_name = re.sub(r"([0-9]+(\.[0-9]+)?)", r" \1", ch_name).strip().replace('  ', ' ')

        ch_id = c['id']
        ch_img = c['image_square']['url'].replace('{width}', '500').replace('{height}', '500')

        ar_chan.append([ch_code, ch_name, ch_img, ch_id])

    if order == 1:
        ar_chan = sorted(ar_chan, key=lambda x: x[1])

    return ar_chan


def replay_channels_gen():
    channels = replay_channels_array_gen()
    for ch in channels:
        li = xbmcgui.ListItem(ch[1])
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': ch[1], 'sorttitle': ch[1], 'plot': ''})
        if ch[2]:
            li.setArt({'thumb': ch[2], 'poster': ch[2], 'banner': banner, 'icon': icon, 'fanart': fanart})
        else:
            li.setArt({'thumb': thumb, 'poster': poster, 'banner': banner, 'icon': icon, 'fanart': fanart})
        url_ch = build_url({'mode': 'replay', 'action': 'date', 'ch_code': ch[0], 'ch_img': ch[2]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=True)

    set_view()
    xbmcplugin.endOfDirectory(addon_handle)


def replay_calendar_gen(ch_code, channel_img):
    time_now = int(time.time())

    ar_date = []
    i = 0
    while i <= 6:
        day = time_now - i * 24 * 60 * 60
        ar_date.append(get_date(day))
        i = i + 1

    for date in ar_date:
        li = xbmcgui.ListItem(date)
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': date, 'sorttitle': date, 'plot': ''})
        li.setArt({'thumb': channel_img, 'poster': channel_img, 'banner': banner, 'icon': icon, 'fanart': fanart})
        url_ch = build_url({'mode': 'replay', 'action': 'prog', 'date': date, 'ch_code': ch_code, 'ch_img': channel_img})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=True)

    set_view()
    xbmcplugin.endOfDirectory(addon_handle)


def add_zero(x):
    if x <= 9:
        return '0' + str(x)
    else:
        return str(x)


def get_date(x):
    ts = time.localtime(x)
    return str(ts.tm_year) + '-' + str(add_zero(ts.tm_mon)) + '-' + str(add_zero(ts.tm_mday))


def replay_programs_array_gen(ch_code, date, retry=0):
    retry += 1

    url = 'https://tvpstream.tvp.pl/api/tvp-stream/program-tv/index?station_code={code}&date={date}'.format(code=ch_code, date=date)

    response = get_requests(url)
    try:
        pr_data = response['data']
    except:
        time.sleep(1)
        if retry < 6:
            return replay_programs_array_gen(ch_code, date, retry)
        else:
            xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
            raise source_exception('Error loading list')

    ar_prog = []

    time_now = int(time.time()) * 1000

    def hm(t):
        ts = time.localtime(t / 1000)
        return add_zero(ts.tm_hour) + ':' + add_zero(ts.tm_min)

    for p in pr_data:
        if p['date_start'] < time_now:
            p_id = p['record_id']
            ch_code = p['station_code']

            ch_name = p['station']['name'].replace('EPG - ', '')
            ch_name = re.sub(r"([0-9]+(\.[0-9]+)?)", r" \1", ch_name).strip().replace('  ', ' ')

            p_title = p['title']
            p_desc = p['description']
            p_time_delta = '[COLOR 80FFFFFF][B][{0} - {1}][/B][/COLOR]'.format(hm(p['date_start']), hm(p['date_end']))

            p_logo = ''
            program = p.get('program')
            if program is not None:
                cycle = program.get('cycle')
                if cycle is not None:
                    logo = cycle['image_logo']
                    if logo:
                        p_logo = logo['url'].replace('{width}', '360').replace('{height}', '205')

            ar_prog.append([p_id, ch_code, p_title, p_desc, p_time_delta, p_logo, ch_name])

    return ar_prog


def replay_programs_gen(ch_code, ch_img, date):
    programs = replay_programs_array_gen(ch_code, date)
    for p in programs:
        channel = '[COLOR {0}][B] {1} [/B][/COLOR]'.format(colors[color], p[6])

        if form == 0:
            title = '{0} {1} - {2}'.format(channel, p[4], p[2])
        else:
            title = '{0} {1} - {2}'.format(channel, p[2], p[4])

        li = xbmcgui.ListItem(title)
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': title, 'sorttitle': p[2], 'plot': p[3]})
        if p[5]:
            li.setArt({'thumb': p[5], 'poster': p[5], 'banner': banner, 'icon': icon, 'fanart': fanart})
        else:
            li.setArt({'thumb': ch_img, 'poster': ch_img, 'banner': banner, 'icon': icon, 'fanart': fanart})
        url_ch = build_url({'mode': 'replay', 'action': 'play', 'ch_code': p[1], 'prog_id': p[0]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=False)

    set_view()
    xbmcplugin.endOfDirectory(addon_handle)


def get_replay_program_streams(ch_code, prog_id, retry=0):
    retry += 1

    url = ' https://sport.tvp.pl/api/tvp-stream/stream/data?station_code={code}&record_id={prog}'.format(code=ch_code, prog=prog_id)

    response = get_requests(url)
    try:
        replay = response['data']
    except:
        time.sleep(1)
        if retry < 6:
            return get_replay_program_streams(code, prog_id, retry)
        else:
            xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
            raise source_exception('Error loading list')

    urls = replay['stream_url']
    response = get_requests(urls)
    streams = response['formats']

    return streams


def apply_timeshift(url_stream, keep_begin_time=True):
    if url_stream is not None:
        time_delta = int(addon.getSetting('tvpgo_timeshift_delta_value'))
        if addon.getSetting('tvpgo_timeshift_type') == strings(30004) and time_delta > 0 and time_delta <= 10080:
            url_stream = adjust_timeshift_args(url_stream, begin_time=gen_begin_time_from_timedelta(time_delta))
        else:
            url_stream = adjust_timeshift_args(url_stream, keep_begin_time=keep_begin_time)

        return url_stream


def adjust_timeshift_args(inputUrl, begin_time=None, keep_begin_time=True):
    input_url_parsed = urllib_parse.urlparse(inputUrl)
    input_params = dict(urllib_parse.parse_qsl(input_url_parsed.query))

    if not keep_begin_time:
        del input_params['begin']

    if begin_time is not None:
        input_params['begin'] = begin_time

    input_params['end'] = ''

    inputUrlList = list(input_url_parsed)
    inputUrlList[4] = urllib_parse.urlencode(input_params)

    return urllib_parse.urlunparse(inputUrlList)


def gen_begin_time_from_timedelta(delta_min):
    time_now = int(time.time())

    begin_timestamp = time_now - delta_min * 60
    utc_begin_time_object = datetime.datetime.utcfromtimestamp(begin_timestamp)
    time_format_pattern = '%Y%m%dT%H%M%S'

    return utc_begin_time_object.strftime(time_format_pattern)


def get_stream_of_type(streams, force=False):
    url_stream = ''

    for s in streams:
        if (s['mimeType'] == 'application/dash+xml' and not ('mobile' in s['url'])):
            url_stream = s['url']
            protocol = 'mpd'
            mime_type = 'application/xml+dash'

        elif (s['mimeType'] == 'application/x-mpegurl' and not ('mobile' in s['url'])):
            url_stream = s['url']
            protocol = 'hls'
            mime_type = 'application/x-mpegurl'

        elif (s['mimeType'] == 'video/mp2t' and not ('mobile' in s['url'])):
            url_stream = s['url']
            protocol = 'hls'
            mime_type = 'video/mp2t'

    if url_stream != '':
        return url_stream, protocol, mime_type
    else:
        xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
        raise source_exception('Error loading list')


def play_programme(code, prog_id):
    streams = get_replay_program_streams(code, prog_id)
    url_stream, protocol, mime_type = get_stream_of_type(streams)
    play(url_stream, protocol, mime_type)


def play(url_stream, protocol, mime_type=None):
    import inputstreamhelper
    PROTOCOL = protocol

    is_helper = inputstreamhelper.Helper(PROTOCOL)
    if is_helper.check_inputstream():
        play_item = xbmcgui.ListItem(path=url_stream)
        if mime_type is not None:
            play_item.setMimeType(mime_type)
        play_item.setContentLookup(False)
        if sys.version_info >= (3, 0, 0):
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
        else:
            play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)

        play_item.setProperty("IsPlayable", "true")
        play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)

    xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)


def generate_m3u(c):
    if file_name == '' or path_m3u == '':
        xbmcgui.Dialog().notification('TVP GO', strings(30022), xbmcgui.NOTIFICATION_ERROR)
        return

    xbmcgui.Dialog().notification('TVP GO', strings(30025), xbmcgui.NOTIFICATION_INFO)
    data = '#EXTM3U\n'

    for item in c:
        ch_code = item[0]
        ch_name = item[1]
        ch_logo = item[2]
        if ch_code == '':
            ch_id = item[3]
        else:
            ch_id = ''
        data += '#EXTINF:0 tvg-id="{0}" tvg-logo="{1}" group-title="TVPGO",{2}\nplugin://plugin.video.tvpgo?mode=list&ch_code={3}&ch_id={4}\n'.format(ch_name,
                                                                                                                                                      ch_logo,
                                                                                                                                                      ch_name,
                                                                                                                                                      ch_code,
                                                                                                                                                      ch_id)

    f = xbmcvfs.File(path_m3u + file_name, 'w')
    f.write(data)
    f.close()

    xbmcgui.Dialog().notification('TVP GO', strings(30029), xbmcgui.NOTIFICATION_INFO)


class Main(SimplePlugin):
    def home(self):
        mode = params.get('mode', None)
        action = params.get('action', '')

        if mode:
            if mode == 'live':
                if action == 'getChannels':
                    self.channels_gen()
                if action == 'play':
                    channel_code = params.get('ch_code', '')
                    channel_id = params.get('ch_id', '')
                    play_channel(channel_code, channel_id)

            if mode == 'replay':
                if action == 'getChannels':
                    replay_channels_gen()
                if action == 'date':
                    channel_code = params.get('ch_code', '')
                    channel_img = params.get('ch_img', '')
                    replay_calendar_gen(channel_code, channel_img)
                if action == 'prog':
                    channel_code = params.get('ch_code', '')
                    date = params.get('date', '')
                    channel_img = params.get('ch_img', '')
                    replay_programs_gen(channel_code, channel_img, date)
                if action == 'play':
                    channel_code = params.get('ch_code', '')
                    program_id = params.get('prog_id', '')
                    date = params.get('date', '')
                    play_programme(channel_code, program_id)

            if mode == 'list':
                channel_code = params.get('ch_code', '')
                channel_id = params.get('ch_id', '')
                play_channel(channel_code, channel_id)

        else:
            if not action:
                self.main_menu()
            if action == 'BUILD_M3U':
                ar_chan = self.channel_array_gen()
                generate_m3u(ar_chan)

    def main_menu(self):
        items = [
            ['Kanały na żywo', 'live', 'getChannels'],
            ['Replay', 'replay', 'getChannels']
        ]
        with self.directory() as kdir:
            for item in items:
                self.url_ch = self.mkurl('?mode=live&action=getChannels')
                kdir.menu(item[0], call(self.channels_gen, url=self.url_ch), info={'title': item[0], 'sorttitle': item[0], 'plot': ''},
                          art={'thumb': thumb, 'poster': poster, 'banner': banner, 'icon': icon, 'fanart': fanart})

    def channel_array_gen(self, retry=0):
        retry += 1

        url = "https://tvpstream.tvp.pl/api/tvp-stream/program-tv/stations"

        response = get_requests(url)
        try:
            ch_data = response['data']
        except:
            time.sleep(1)
            if retry < 6:
                return self.channel_array_gen(retry)
            else:
                xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
                raise source_exception('Error loading list')

        ar_chan = []
        for c in ch_data:
            ch_id = c['id']
            ch_code = c['code']

            ch_name = c['name'].replace('EPG - ', '')
            ch_name = re.sub(r"([0-9]+(\.[0-9]+)?)", r" \1", ch_name).strip().replace('  ', ' ')

            ch_img = c['image_square']['url'].replace('{width}', '500').replace('{height}', '500')

            ar_chan.append([ch_code, ch_name, ch_img, ch_id])

        if order == 1:
            ar_chan = sorted(ar_chan, key=lambda x: x[1])

        return ar_chan

    def channels_gen(self, url):
        from datetime import datetime

        channels = self.channel_array_gen()
        epg_data = get_epgs()

        with self.directory() as kdir:
            for ch in channels:
                p_live = ''
                p_start = ''
                p_end = ''
                p_duration = ''
                p_title = ''
                p_year = ''
                p_land = ''
                p_desc = ''
                p_desc_long = ''
                p_img = ''

                for epg in epg_data:
                    if ch[0] == epg[1]:
                        p_live = epg[2]
                        p_start = epg[3]
                        p_end = epg[4]
                        p_duration = epg[5]
                        p_title = epg[6]
                        p_year = epg[7]
                        p_land = epg[8]
                        p_desc = epg[9]
                        p_desc_long = epg[10]
                        p_img = epg[11]

                if p_start != '' and p_end != '':
                    dt_start = datetime.fromtimestamp(int(p_start) / 1000)
                    dt_end = datetime.fromtimestamp(int(p_end) / 1000)

                    start = dt_start.strftime("%H:%M")
                    end = dt_end.strftime("%H:%M")

                    if p_title != '':
                        channel = '[COLOR {0}][B] {1} [/B][/COLOR]'.format(colors[color], ch[1])
                        time_delta = '[COLOR 80FFFFFF][B][{0} - {1}][/B][/COLOR]'.format(start, end)

                        if form == 0:
                            title = '{0} {1} - {2}'.format(channel, time_delta, p_title)
                        else:
                            title = '{0} {1} - {2}'.format(channel, p_title, time_delta)
                else:
                    title = '[COLOR {0}][B] {1} [/B][/COLOR]'.format(colors[color], ch[1])

                if ch[2]:
                    self.art = ({'thumb': ch[2], 'poster': p_img, 'banner': banner, 'icon': ch[2], 'fanart': p_img})
                else:
                    self.art = ({'thumb': thumb, 'poster': poster, 'banner': banner, 'icon': icon, 'fanart': fanart})
                kdir.play(title, call(self.play_channel, code=ch[0], ch_id=ch[3]), art=self.art,
                          info={'title': title, 'sorttitle': title, 'tvshowtitle': title, 'status': p_live, 'year': p_year, 'plotoutline': p_desc,
                                'plot': p_desc_long, 'duration': p_duration})

    def play_channel(self, code, ch_id, retry=0):
        retry += 1

        url = 'https://tvpstream.tvp.pl/api/tvp-stream/stream/data?station_code={code}'.format(code=code)

        response = get_requests(url)
        try:
            live = response['data']
            if live:
                urls = live['stream_url']
                response = get_requests(urls)

                streams = response['formats']

        except:
            time.sleep(1)
            if retry < 6:
                return self.play_channel(code, ch_id, retry)
            else:
                xbmcgui.Dialog().notification(strings(30027), strings(30028), xbmcgui.NOTIFICATION_INFO, 6000, False)
                raise source_exception('Error loading list')

        url_stream, protocol, mime_type = get_stream_of_type(streams)
        url_stream = apply_timeshift(url_stream)
        play(url_stream, protocol, mime_type)


if __name__ == '__main__':
    Main().run()
