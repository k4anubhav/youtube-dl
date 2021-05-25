from __future__ import unicode_literals
from .common import InfoExtractor
from ..utils import dict_get, int_or_none, ExtractorError


class SkillShareCourseIE(InfoExtractor):

    _VALID_URL = r'https?://(?:www\.)?skillshare.com/classes/[^/]+/(?P<id>[0-9]+)'
    _API_BASE = r'https://api.skillshare.com'
    pk = 'BCpkADawqM2OOcM6njnM7hf9EaK6lIFlqiXB0iWjqGWUQjU7R8965xUvIQNqdQbnDTLz0IAO7E6Ir2rIbXJtFdzrGtitoee0n1XXRliD-RH9A-svuvNW9qgo3Bh34HEZjXjG4Nml4iyz3KqF'
    brightcove_account_id = 3695997568001

    headers = {
        'Accept': 'application/vnd.skillshare.class+json;,version=0.8',
        'User-Agent': 'Skillshare/5.3.13; Android 9.0.1',
        'Host': 'api.skillshare.com',
        'cookie': '',
    }

    login_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'User-Agent': 'Skillshare/5.3.13; Android 9.0.1',
        'Host': 'api.skillshare.com',
        'cookie': '',
    }

    brightcove_headers = {
        'Accept': 'application/json;pk={}'.format(pk),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 Edg/86.0.622.69',
        'Origin': 'https://www.skillshare.com',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty'
    }

    # TODO: ADD TEST CASES
    _TEST = {
        'url': 'https://skillshare.com/classes/Productivity-Masterclass-Create-a-Custom-System-that-Works/442860604?via=search-layout-grid',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '442860604',
            'ext': 'mp4',
            'title': 'Video title goes here',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }

    def _real_extract(self, url, *args, **kwargs):

        str_cookie = ''
        first = True
        for cok in self._downloader.cookiejar:
            if first:
                str_cookie += f'{cok.name}={cok.value}'
                first = False
            else:
                str_cookie += f'; {cok.name}={cok.value}'

        playlist_id = self._match_id(url)

        self.headers.update({'cookie': str_cookie})
        self.login_headers.update({'cookie': str_cookie})
        login_data = self.check_logged_in()

        if login_data.get('logged-in'):
            class_data = self._download_json(
                '%s/classes/%s' % (self._API_BASE, playlist_id),
                playlist_id,
                headers=self.headers
            )

            if class_data.get('enrollment_type') == 0 or login_data.get('premium'):
                class_title, teacher_name, videos_data = self.black_black(class_data=class_data)
                videos_data = self.update_videos_data(videos_data)
            else:
                raise ExtractorError(
                    'This video is only available for premium users. You need a premium account to download this video.',
                    expected=True)

        else:
            raise ExtractorError(
                'This video is only available for registered users. You may want to use --cookies.', expected=True)
        print(playlist_id)
        # TODO more code goes here, for example ...

        return self.playlist_result(entries=videos_data, playlist_id=playlist_id, playlist_title=class_title)

    def get_video_data(self, video_hashed_id):
        meta_url = 'https://edge.api.brightcove.com/playback/v1/accounts/{account_id}/videos/{video_hashed_id}'.format(
            account_id=self.brightcove_account_id,
            video_hashed_id=video_hashed_id,
        )
        video_data = self._download_json(
            meta_url,
            video_hashed_id,
            headers=self.brightcove_headers
        )
        return video_data

    def check_logged_in(self):
        res_data = {
            "logged-in": False,
            "premium": False,
            "Username": None,
            "Full Name": None
        }

        res = self._download_json(
            url_or_request='%s/me' % self._API_BASE,
            video_id=None,
            headers=self.login_headers,
            expected_status=(200, 401,))

        data = res

        if data.get('errors'):
            if data.get('errors')[0].get('code') == 135:
                return res_data
            else:
                return res_data
        else:
            res_data.update({
                "logged-in": True,
                "premium": data.get('is_member'),
                "Username": data.get('username'),
                "Full Name": data.get('full_name')})
            return res_data

    @staticmethod
    def safe_get(dct, *keys):
        for key in keys:
            try:
                dct = dct[key]
            except KeyError:
                return None
        return dct

    def black_black(self, class_data):

        teacher_name = dict_get(self.safe_get(class_data, '_embedded', 'teacher'), ['vanity_username', 'full_name'])

        class_title = class_data.get('title')

        videos_data = []

        for units in self.safe_get(class_data, '_embedded', 'units', '_embedded', 'units'):
            for sessions in self.safe_get(units, '_embedded', 'sessions', '_embedded', 'sessions'):
                if 'video_hashed_id' in sessions:
                    if sessions.get('video_hashed_id'):
                        video_hashed_id = sessions.get('video_hashed_id').split(':')[1]

                        if not video_hashed_id:
                            continue

                        videos_data.append({
                            'video_hashed_id': video_hashed_id,
                            'title': sessions.get('title'),
                            'video_duration': int_or_none(sessions.get('video_duration_seconds')),
                            'thumbnail': sessions.get('video_thumbnail_url'),
                            'index': sessions.get('index')})

        return class_title, teacher_name, videos_data

    def get_format(self, src_link, video_id, f_type):
        formats = None
        if f_type == 'm3u8':
            formats = self._extract_m3u8_formats(
                src_link,
                video_id,
                m3u8_id='hls',
                fatal=False)
        elif f_type == 'mpd':
            formats = self._extract_mpd_formats(
                src_link,
                video_id,
                mpd_id='dash',
                fatal=False)
        return formats

    def update_videos_data(self, videos_data):
        for video_dt in videos_data:
            video_dt.update(self.video_data_from_video_hashed_id(video_dt.get('video_hashed_id')))
        return videos_data

    def video_data_from_video_hashed_id(self, video_hashed_id):
        res_template = {
            'id': None,
            'url': None,
            'thumbnail': None,
            'subtitles': None,
            'duration': None,
            'formats': None,
        }
        meta_url = 'https://edge.api.brightcove.com/playback/v1/accounts/{account_id}/videos/{video_hashed_id}'.format(
            account_id=self.brightcove_account_id,
            video_hashed_id=video_hashed_id)

        meta_data = self._download_json(
            meta_url,
            video_id=video_hashed_id,
            headers=self.brightcove_headers)

        video_id = meta_data.get('id')

        # TODO: Add Different Resolution Download
        for sources in meta_data.get('sources'):
            if sources.get('container') == 'MP4' and 'src' in sources:
                res_template.update({
                    'id': video_id,
                    'url': sources.get('src'),
                    'duration': sources.get('duration')})
                break
        else:
            # m3u8 or mpd download needs ffmpeg (For most courses, don't need ffmpeg)
            formats = {}
            for sources in meta_data.get('sources'):
                if sources.get('type') == 'application/x-mpegURL' and sources.get('ext_x_version') == '4' and 'src' in sources:
                    formats = (self.get_format(
                        sources.get('src'),
                        video_id,
                        'm3u8'))
                    break
                elif sources.get('type') == 'application/dash+xml' and 'src' in sources:
                    formats = (self.get_format(
                        sources.get('src'),
                        video_id,
                        'mpd'))

            res_template.update({
                'id': video_id,
                'formats': formats})

        subtitles = {}
        for text_track in meta_data.get('text_tracks'):
            if not isinstance(text_track, dict):
                continue
            lang = text_track.get('srclang') or 'en'
            url = None
            for sources in text_track.get('sources'):
                url = sources.get('src')
                if url:
                    break
            subtitles.setdefault(lang, []).append({
                'url': url,
            })

        if subtitles != {}:
            print(subtitles, 'subs')
            res_template.update({
                'subtitles': subtitles})

        return res_template
