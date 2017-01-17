from beets.plugins import BeetsPlugin

import dnuos

class AlbumQualityPlugin(BeetsPlugin):
    def __init__(self):
        super(AlbumQualityPlugin, self).__init__()

        self.album_template_fields['albumquality'] = _tmpl_album_quality


def _tmpl_album_quality(album):
    items = album.items()

    if not len(items):
        return
    
    first_track_path = items[0].path
    mp3 = dnuos.MP3(first_track_path)

    try:
        return mp3.profile()
    except Exception as ex:
        return 'Unknown'