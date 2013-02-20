#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import itertools
from subprocess import Popen, PIPE
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis


RSYNC_CMDLINE =  ['rsync', '--modify-window=3602', '--recursive', #'--update',
                  '--times', '--delete', '--delete-before', '--delete-excluded',
                  '--log-format=%n']#, '--dry-run']
def rsync(source, dest, excludes, cmdline=RSYNC_CMDLINE):
    """

    """
    proc = Popen(cmdline + ['--exclude=%s' % excl for excl in excludes] +
                  [source, dest], stdout=PIPE)
    files = []
    while True:
        line = proc.stdout.readline()
        if not line: break
        sys.stdout.write(line)
        if not line.startswith('deleting '):
            files.append(dest + line.replace('\n', ''))
    return files


def unsort(name):
    joiner = ''
    parts = [name]
    if ' & ' in name:
        joiner = ' & '
        parts = name.split(' & ')
    elif ' and ' in name:
        joiner = ' and '
        parts = name.split(' and ')

    if name == u"Taylor, James Quartet, The":
        return u"The James Taylor Quartet"

    def proc_parts(part):
        lst = part.split(', ')
        if len(lst) > 2 and lst[-1] != u"The":
            return  u' '.join(reversed(lst[:-1])) + u' ' +  lst[-1]
        else:
            return u' '.join(reversed(lst))

    return joiner.join(map(proc_parts, parts))


EasyID3.RegisterTextKey('albumartist', 'TPE2')
EasyID3.RegisterTextKey('originaldate', 'TDOR')

disposable_fields = ['musicbrainz_trackid', 'musicbrainz_artistid',
                     'musicbrainz_albumid', 'musicbrainz_albumartistid',
                     'musicbrainz_discid', 'albumartistsort']

def fix_tags(files):
    """

    """
    mp3s = filter(lambda line: line.endswith('.mp3'), files)
    oggs = filter(lambda line: line.endswith('.ogg'), files)
    flacs = filter(lambda line: line.endswith('.flac'), files)

    mp3s = (EasyID3(mp3) for mp3 in mp3s)
    oggs = (OggVorbis(ogg) for ogg in oggs)
    flacs = (FLAC(flac) for flac in flacs)

    for tags in itertools.chain(oggs, mp3s, flacs):
        try:
            has_changes = False
            current_size = os.path.getsize(tags.filename)
            artist = tags['artist'][0]
            artist_len = len(artist.encode('utf-8'))
            album = tags['album'][0]
            album_len = len(album.encode('utf-8'))
            title = tags['title'][0]
            title_len = len(title.encode('utf-8'))

            if 'albumartistsort' in tags:
                albumartistsort = tags['albumartistsort'][0]
                albumartist = tags.get('albumartist', [unsort(albumartistsort)])[0]
                #albumartist = unsort(albumartistsort)

                if albumartist == ' '.join(artist.split("'s ")) or\
                   albumartist == "'".join(artist.split(u"\u02bb")) or \
                   (albumartist == u"Turboneger" and artist == u"Turbonegro"):
                    albumartist = artist
                if albumartist == u"The Jimi Hendrix Experience":
                    albumartist = "Jimi Hendrix"
                if u"..." + albumartistsort == albumartist:   # Trail of Dead
                    tags['artist'] = albumartistsort
                    albumartist = artist
                    has_changes = True
                if albumartist != artist:
                    tags['artist'] = albumartist
                    if artist.startswith(albumartist + u" feat. ") or\
                       artist.startswith(albumartist + u" fiitsch. "): # Tomazobi        # or \
#                       artist.startswith(albumartist + u" with ") or \
#                       artist.startswith(albumartist + u" mit ") or \
#                       artist.startswith(albumartist + u" & ") or \
#                       artist.startswith(albumartist + u" and ") or \
#                       artist.startswith(albumartist + u" und "):
                        tags['title'] = u"%s (%s)" % (title, artist[len(albumartist) + 1:])
                    elif artist.startswith(albumartist + u", "):
                        tags['title'] = u"%s (%s)" % (title, artist[len(albumartist) + 2:])
                    else:
                        tags['title'] = u"%s (%s)" % (title, artist)

                    tags['artist'] = albumartist
                    has_changes = True
            else:
                print u"No albumartistsort in %s" % tags.filename

            if 'originaldate' in tags:
                originaldate = str(tags['originaldate'][0])
                originalyear = originaldate[:4]
                if not album.startswith(originalyear):
                    tags['album'] = u"%s - %s" % (originalyear, album)
                    has_changes = True
            else:
                print u"No date in %s" % tags.filename
                
            if 'disctotal' in tags and 'discnumber' in tags:
                discs = int(tags['disctotal'][0])
                if discs > 1:
                    tags['album'] = u"%s - Disc %s" % (tags['album'][0],
                                                       tags['discnumber'][0])
                    has_changes = True

            if has_changes:
                mtime = os.path.getmtime(tags.filename)
                if isinstance(tags, OggVorbis):  # Prevent file size increase
                    bytes = len(tags['artist'][0].encode('utf-8')) - artist_len
                    bytes += len(tags['album'][0].encode('utf-8')) - album_len
                    bytes += len(tags['title'][0].encode('utf-8')) - title_len
                    assert bytes >= 0, 'bytes negative'
                    for field in disposable_fields:
                        if field in tags:
                            value = tags[field][0]
                            if len(value) >= bytes:
                                tags[field] = value[bytes:]
                                bytes = 0
                                break
                            else:
                                tags[field] = ''
                                bytes -= len(value)
                    assert bytes == 0, 'bytes not zero'
                tags.save()
                os.utime(tags.filename, (mtime, mtime))
                print [tags['artist'], tags['album'], tags['title']]
                assert os.path.getsize(tags.filename) == current_size, 'different size: %s vs %s' % (os.path.getsize(tags.filename), current_size)
        except Exception, e:
            print >>sys.stdout, 'Error!'
            print >>sys.stdout, tags.filename
            print >>sys.stdout, e
            print "Error: %s" % e.message


        sys.stdout.flush()


def main():
    """

    """
    source = '/home/marco/musig/sorted/'
    if not source.endswith(os.sep):
        source += os.sep
    dest_internal = '/media/COWON J3/Music'
    if not dest_internal.endswith(os.sep):
        dest_internal += os.sep
    dest_microsd = '/media/MicroSD/Music'
    if not dest_microsd.endswith(os.sep):
        dest_microsd += os.sep

    df = Popen(['df "%s"' % dest_internal], shell=True, stdout=PIPE)
    internal_capacity = int(df.stdout.read().splitlines()[1].split()[1])
    internal_capacity -= 1024 * 150   # 150MiB reserve
    del df

    du  = Popen(['du -s *' ], shell=True, stdout=PIPE, cwd=source)
    lines = du.stdout.read().splitlines()
    lines = [(int(line.split()[0]), line.split()[1]) for line in lines]
    del du

    pivot = 0
    total_usage = 0
    for line, (usage, folder) in enumerate(lines, 1):
        total_usage += usage
        if total_usage >= internal_capacity:
            break
        pivot = line

    to_internal = [folder for usage, folder in lines[:pivot]]
    to_microsd = [folder for usage, folder in lines[pivot:]]

    files_internal = rsync(source, dest_internal, excludes=to_microsd)
    files_microsd = rsync(source, dest_microsd, excludes=to_internal)

    fix_tags(files_internal + files_microsd)

if __name__ == '__main__':
    main()
