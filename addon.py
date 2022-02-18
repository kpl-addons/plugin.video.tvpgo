# -*- coding: utf-8 -*-
import os
import sys

import six
from six.moves import urllib_error, urllib_request, urllib_parse, http_cookiejar

import urllib
import requests
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import urllib3
import re
import json
import random
import time
import datetime

from collections import OrderedDict

try:
    from urllib.parse import urlencode, quote_plus, quote, unquote
except ImportError:
    from urllib import urlencode, quote_plus, quote, unquote
    
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(urllib_parse.parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.tvpgo')
file_name = addon.getSetting('fname')
path_m3u = addon.getSetting('path_m3u')

mode = addon.getSetting('mode')

addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))

thumb =  os.path.join(addon_path, 'resources', 'art', 'landscape.png')
poster = os.path.join(addon_path, 'resources', 'art', 'poster.png')
banner = os.path.join(addon_path, 'resources', 'art', 'banner.png')
icon = os.path.join(addon_path, 'icon.png')
fanart = os.path.join(addon_path, 'fanart.png')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.80 Safari/537.36 Edg/98.0.1108.50'

def build_url(query):
    return base_url + '?' + urllib_parse.urlencode(query)

def main_menu():
    items = [
        ['Kanały na żywo','live','getChannels'],
        ['Replay', 'replay','getChannels']
        ]

    for i in items:
        li = xbmcgui.ListItem(i[0])
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': i[0],'sorttitle': i[0],'plot': ''})
        li.setArt({'thumb': thumb, 'poster': poster, 'banner': banner, 'icon': icon, 'fanart': fanart})
        url_ch = build_url({'mode':i[1],'action':i[2]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)


def channelArrayGen():
    try:
        data = {
            'operationName': None,
            'variables': {
                'categoryId': None,
            },
            'extensions': {
                'persistedQuery': {
                    'version': 1,
                    'sha256Hash': '5c29325c442c94a4004432d70f94e336b8c258801fe16946875a873e818c8aca',
                },
            
            'query': """
        query ($categoryId: String) {
          getLandingPageVideos(categoryId: $categoryId) {
            type
            title
            elements {
              id
              title
              subtitle
              type
              img {
                hbbtv
                image
                website_holder_16x9
                video_holder_16x9
                __typename
              }
              broadcast_start_ts
              broadcast_end_ts
              sportType
              label {
                type
                text
                __typename
              }
              stats {
                video_count
                __typename
              }
              __typename
            }
            __typename
          }
          getStationsForMainpage {
            items {
              id
              name
              title
              code
              image_square {
                url
                __typename
              }
              background_color
              isNativeChanel
              __typename
            }
            __typename
          }
        }""" 
            }
        }

        response = requests.post('https://hbb-prod.tvp.pl/apps/manager/api/hub/graphql', json=data).json()

        ch_data = response['data']['getStationsForMainpage']['items']

        ar_chan = []
        for c in ch_data:
            ch_code = c['code']
            ch_name = c['name'].replace('EPG - ', '')

            if ch_code == '':
                ch_id = c['id']
                ch_img = c['image_square']['url'].replace('{width}','1000').replace('{height}','500')
            else:
                ch_id = ''
                ch_img = c['image_square']['url'].replace('{width}','140').replace('{height}','140')
            ar_chan.append([ch_code, ch_name, ch_img, ch_id])
        return ar_chan
    
    except Exception as ex:
        xbmc.log('TVP GO channelArrayGen Exception: {}'.format(ex), level=0)
    
def channels_gen():
    channels = channelArrayGen()
    for ch in channels:
        li = xbmcgui.ListItem(ch[1])
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': ch[1],'sorttitle': ch[1],'plot': ''})
        if ch[2]:
            li.setArt({'thumb': ch[2], 'poster': poster, 'banner': banner, 'icon': icon, 'fanart': fanart})
        else:
            li.setArt({'thumb': thumb, 'poster': poster, 'banner': banner, 'icon': icon, 'fanart': fanart})
        url_ch = build_url({'mode':'live','action':'play','chCode':ch[0],'chID':ch[3]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def applyTimeShift(url_stream, keepBeginTime=True):
    time_delta = int(addon.getSetting('timeshift_delta_value'))
    if addon.getSetting('timeshift_type') == 'O stałą wartość' and time_delta > 0 and time_delta <= 10080:
        url_stream = adjustTimeShiftArguments(url_stream, beginTime=generateBeginTimeFromTimeDelta(time_delta))
    else:
        url_stream = adjustTimeShiftArguments(url_stream, keepBeginTime=keepBeginTime)
    return url_stream

def adjustTimeShiftArguments(inputUrl, beginTime = None, keepBeginTime = True):
    inputUrlParsed = urllib_parse.urlparse(inputUrl)
    inputParams = dict(urllib_parse.parse_qsl(inputUrlParsed.query))
    
    if not keepBeginTime:
        del inputParams['begin']
    
    if beginTime is not None:
        inputParams['begin'] = beginTime

    inputParams['end'] = ''

    inputUrlList = list(inputUrlParsed)
    inputUrlList[4] = urllib_parse.urlencode(inputParams)

    return urllib_parse.urlunparse(inputUrlList)

def generateBeginTimeFromTimeDelta(timeDeltaInMinutes):
    time_now = int(time.time())
    begin_timestamp = time_now-timeDeltaInMinutes*60
    utc_begin_time_object = datetime.datetime.utcfromtimestamp(begin_timestamp)
    time_format_pattern = '%Y%m%dT%H%M%S'
    return utc_begin_time_object.strftime(time_format_pattern)

def getStreamOfType(streams, mimeType):
    for s in streams:
        if (s['mimeType'] == mimeType and not ('mobile' in s['url'])):
            url_stream = s['url']
            break

    return url_stream

def getProgram(chCode, progID):
    try:
        streams = getReplayProgramStreams(chCode, progID)
        url_stream = getStreamOfType(streams, 'application/x-mpegurl')
        play(url_stream, 'hls', 'application/x-mpegurl')

    except Exception as ex:
        xbmc.log('TVP GO getProgram Exception: {}'.format(ex), level=0)

def getStream(chCode, chId):
    if chCode != '':
        data = {
            'operationName': None,
            'variables': {
                'stationCode': '{0}'.format(chCode),
            },
            'extensions': {
                'persistedQuery': {
                    'version': 1,
                    'sha256Hash': '0b9649840619e548b01c33ae4bba6027f86eac5c48279adc04e9ac2533781e6b',
                },
            
            'query': """
        query ($stationCode: String!) {
          currentProgramAsLive(stationCode: $stationCode) {
            id
            title
            subtitle
            date_start
            date_end
            date_current
            description
            description_long
            description_akpa_long
            description_akpa_medium
            description_akpa
            plrating
            npvr
            formats {
              mimeType
              url
              __typename
            }
            __typename
          }
        }
        }""" 
        }
        }

        response = requests.post('https://hbb-prod.tvp.pl/apps/manager/api/hub/graphql', json=data).json()

        if response['data']['currentProgramAsLive'] is not None:
            streams = response['data']['currentProgramAsLive']['formats']
            url_stream = getStreamOfType(streams, 'application/dash+xml')
            url_stream = applyTimeShift(url_stream)
            play(url_stream, 'mpd', 'application/xml+dash')
        else:
            anyProgramme = replayProgramsArrayGen(chCode, getDate(int(time.time())))[0]
            streams = getReplayProgramStreams(chCode, anyProgramme[0])
            url_stream = getStreamOfType(streams, 'application/dash+xml')
            url_stream = applyTimeShift(url_stream, False)
            play(url_stream, 'mpd', 'application/xml+dash')

    else:
        data = {
            'operationName': None,
            'variables': {
                'liveId': '{0}'.format(chId),
            },
            'extensions': {
                'persistedQuery': {
                    'version': 1,
                    'sha256Hash': 'f2fd34978dc0aea320ba2567f96aa72a184ca2d1e55b2a16dc0915bd03b54fb3',
                },
            
            'query': """
        query ($liveId: String!) {
          getLive(liveId: $liveId) {
            error
            data {
              type
              title
              subtitle
              lead
              label {
                type
                text
                __typename
              }
              src
              vast_url
              duration_min
              subtitles {
                src
                autoDesc
                lang
                text
                __typename
              }
              is_live
              formats {
                mimeType
                totalBitrate
                videoBitrate
                audioBitrate
                adaptive
                url
                downloadable
                __typename
              }
              web_url
              __typename
            }
            __typename
          }
        }""" 
        }
        }

        response = requests.post('https://hbb-prod.tvp.pl/apps/manager/api/hub/graphql', json=data).json()
        streams = response['data']['getLive']['data'][0]['formats']

        url_stream = getStreamOfType(streams, 'application/x-mpegurl')
        
        if 'material_niedostepny' in url_stream:
            xbmcgui.Dialog().notification('TVP GO', 'Materiał niedostępny')
            return

        headers = {
            'User-Agent' : UA,
        }

        response = requests.get(url_stream, headers=headers, verify=False, timeout=3)
        status = response.status_code

        if status < 400:
            play(url_stream, 'hls', 'application/x-mpegurl')

        else:
            return

def play(url_stream, PROTOCOL, mimeType):
    DRM = 'com.widevine.alpha'

    import inputstreamhelper

    is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
    if is_helper.check_inputstream():
        play_item = xbmcgui.ListItem(path=url_stream)
        play_item.setMimeType(mimeType)
        play_item.setContentLookup(False)
        if sys.version_info >= (3,0,0):
            play_item.setProperty('inputstream', is_helper.inputstream_addon)
        else:
            play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)

        play_item.setProperty('inputstream.adaptive.license_key', url_stream + '|Content-Type=|R{SSM}|')
        play_item.setProperty('inputstream.adaptive.license_type', DRM)
        play_item.setProperty("IsPlayable", "true")
        play_item.setProperty('inputstream.adaptive.stream_headers', 'Referer: https://tvpstream.vod.tvp.pl/&User-Agent='+quote(UA))
        play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)

        xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

def replayChannelsArrayGen(): 
    data = {
        'operationName': None,
        'variables': {},
        'extensions': {
            'persistedQuery': {
                'version': 1,
                'sha256Hash': '18a5c6b18b6443bd317f69ff092b6d7068733640159eaf216c35f583ea73ac23',
            },
        
        'query': """
    {
      getStations {
        items {
          name
          code
          image_square {
            url
            __typename
          }
          background_color
          __typename
        }
        __typename
      }
    }""" 
    }
    }

    response = requests.post('https://hbb-prod.tvp.pl/apps/manager/api/hub/graphql', json=data).json()
    ch_data = response['data']['getStations']['items']
    ar_chan = []
    for ch in ch_data:
        chName = ch['name']
        chCode = ch['code']
        ar_chan.append([chName,chCode])
    return ar_chan
    
def replayChannelsGen():
    array = channelArrayGen()
    channels = replayChannelsArrayGen()

    for ch in channels:
        li = xbmcgui.ListItem(ch[0])
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': ch[0],'sorttitle': ch[0],'plot': ''})

        img = [l[2] for l in array if l[1] == ch[0]][0]
        img = img if img else icon

        if img:
            li.setArt({'thumb': img, 'poster': img, 'banner': banner, 'icon': icon, 'fanart': fanart})

        url_ch = build_url({'mode':'replay','action':'date','chCode':ch[1]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)

def addZero(x): 
        if x <= 9:
            return '0' + str(x)
        else:
            return str(x)

def getDate(x):
    ts = time.localtime(x)
    return str(ts.tm_year) + '-' + str(addZero(ts.tm_mon)) + '-' + str(addZero(ts.tm_mday))

def replayCalendarGen(chCode):
    time_now = int(time.time())
    
    ar_date = []
    i = 0
    while i <= 6:
        day = time_now - i * 24 * 60 * 60
        ar_date.append(getDate(day))
        i = i + 1
    
    for d in ar_date:
        li = xbmcgui.ListItem(d)
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': d,'sorttitle': d,'plot': ''})
        #li.setArt({'thumb': ch[2], 'poster': ch[2], 'banner': ch[2], 'icon': ch[2], 'fanart': ''})
        url_ch = build_url({'mode':'replay','action':'prog','date':d,'chCode':chCode})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(addon_handle)
    
def replayProgramsArrayGen(chCode, date):
    data = {
        'operationName': None,
        'variables': {
            'station_code': '{0}'.format(chCode),
            'categorytvp': '',
        },
        'extensions': {
            'persistedQuery': {
                'version': 1,
                'sha256Hash': '5750d5b161a9ac4e18ae0a5c789d460763ed2bc0835446df9be712017965f8c5',
            },
        
        'query': """
    query ($station_code: String, $date: String, $categorytvp: String) {
      getProgramsFromStation(
        station_code: $station_code
        date: $date
        categorytvp: $categorytvp
      ) {
        total_count
        items {
          id
          record_id
          title
          date_start
          date_end
          duration
          station_code
          description
          description_long
          program {
            has_video_vod
            website_id
            cms_id
            id
            title
            year
            lang
            image {
              type
              title
              point_of_origin
              url
              width
              height
              description
              __typename
            }
            program_type {
              id
              image_logo {
                type
                title
                point_of_origin
                url
                width
                height
                description
                __typename
              }
              title
              __typename
            }
            cycle {
              id
              title
              image_logo {
                type
                title
                point_of_origin
                url
                width
                height
                description
                __typename
              }
              __typename
            }
            __typename
          }
          station {
            id
            name
            code
            image {
              type
              title
              point_of_origin
              url
              width
              height
              description
              __typename
            }
            image_square {
              type
              title
              point_of_origin
              url
              width
              height
              description
              __typename
            }
            background_color
            __typename
          }
          url
          url_canonical
          categories {
            id
            category_type
            title
            __typename
          }
          akpa_attributes
          plrating
          __typename
        }
        __typename
      }
    }""" 
    }
    }

    response = requests.post('https://hbb-prod.tvp.pl/apps/manager/api/hub/graphql', json=data).json()
    pr_data = response['data']['getProgramsFromStation']['items']
    ar_prog = []
    time_now = int(time.time())*1000
    def hm(t):
        ts = time.localtime(t/1000)
        return addZero(ts.tm_hour) + ':' + addZero(ts.tm_min)
    for p in pr_data:
        if p['date_start'] < time_now:
            pID = p['record_id']
            chCode = p['station_code']
            pTitle = '['+hm(p['date_start'])+'-'+hm(p['date_end'])+'] '+p['title']
            pDescr = p['description']
            ar_prog.append([pID, chCode, pTitle, pDescr])

    return ar_prog
    
def replayProgramsGen(chCode,date):
    programs = replayProgramsArrayGen(chCode, date)
    for p in programs:
        li = xbmcgui.ListItem(p[2])
        li.setProperty("IsPlayable", 'true')
        li.setInfo(type='video', infoLabels={'title': p[2],'sorttitle': p[2],'plot': p[3]})
        li.setArt({'thumb': thumb, 'poster': poster, 'banner': banner, 'icon': icon, 'fanart': fanart})
        url_ch = build_url({'mode':'replay','action':'play','chCode':p[1],'progID':p[0]})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_ch, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def getReplayProgramStreams(chCode, progID):
    try:
        data = {
            'operationName': None,
            'variables': {
                'programId': '{0}'.format(progID),
                'stationCode': '{0}'.format(chCode),
            },
            'extensions': {
                'persistedQuery': {
                    'version': 1,
                    'sha256Hash': '52d98fa9bb2b66075e8d230809fd5d991d16fa6a97719b2b4984797f5a506c4a',
                },
            
            'query': """
        query ($programId: String!, $stationCode: String!) {
          programByRecordId(programId: $programId, stationCode: $stationCode) {
            id
            title
            programId
            program_title
            subtitle
            date_start
            date_end
            date_current
            description
            description_long
            description_akpa_long
            description_akpa_medium
            description_akpa
            plrating
            formats {
              mimeType
              url
              __typename
            }
            __typename
          }
        }""" 
        }
        }

        response = requests.post('https://hbb-prod.tvp.pl/apps/manager/api/hub/graphql', json=data).json()
        streams = response['data']['programByRecordId']['formats']

        return streams

    except Exception as ex:
        xbmc.log('TVP GO getReplayProgramStreams Exception: {}'.format(ex), level=0)
            
def generate_m3u(c):
    if file_name == '' or path_m3u == '':
        xbmcgui.Dialog().notification('TVP GO', 'Ustaw nazwe pliku oraz katalog docelowy', xbmcgui.NOTIFICATION_ERROR)
        return
    xbmcgui.Dialog().notification('TVP GO', 'Generuje liste M3U', xbmcgui.NOTIFICATION_INFO)
    data = '#EXTM3U\n'
    for item in c:
        channelCode = item[0]
        channelName = item[1]
        channelLogo = item[2]
        if channelCode=='':
            channelID = item[3]
        else:
            channelID=''
        data += '#EXTINF:0 tvg-id="%s" tvg-logo="%s" group-title="TVPGO",%s\nplugin://plugin.video.tvpgo?mode=list&chCode=%s&chID=%s\n' % (channelName,channelLogo,channelName,channelCode,channelID)

    f = xbmcvfs.File(path_m3u + file_name, 'w')
    f.write(data)
    f.close()
    xbmcgui.Dialog().notification('TVP GO', 'Wygenerowano listę M3U', xbmcgui.NOTIFICATION_INFO)

mode = params.get('mode', None)
action = params.get('action', '')

if mode:
    if mode == 'live':
        if action == 'getChannels':
            channels_gen()

        if action == 'play':
            channel_code = params.get('chCode', '')
            channel_id = params.get('chID', '')
            getStream(channel_code, channel_id)

    if mode == 'replay':
        if action == 'getChannels':
            replayChannelsGen()
        if action == 'date':
            channel_code = params.get('chCode', '')
            replayCalendarGen(channel_code)
        if action == 'prog':
            channel_code = params.get('chCode', '')
            date = params.get('date', '')
            replayProgramsGen(channel_code, date)
        if action == 'play':
            channel_code = params.get('chCode', '')
            program_id = params.get('progID', '')
            date = params.get('date', '')
            getProgram(channel_code, program_id)

    if mode == 'list':
        channel_code = params.get('chCode', '')
        channel_id = params.get('chID', '')
        getStream(channel_code, channel_id)
        
else:
    if not action:
        main_menu()

    if action == 'BUILD_M3U':
        ar_chan = channelArrayGen()
        generate_m3u(ar_chan)#
