#!/usr/bin/python
# -*- coding: UTF-8 -*-
#
#  Copyright (C) 2009 Arkadiusz Miśkiewicz <arekm@pld-linux.org>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# napiprojekt.pl API is used with napiproject administration consent
# (given by Marek <kontakt@napiprojekt.pl> at Wed, 24 Feb 2010 14:43:00 +0100)
#
# napisy24.pl API access granted by napisy24 admins at 15 Feb 2015
#

import StringIO
import re
import sys
import mimetypes
import urllib
import urllib2
import time
import os
import getopt
import socket
import struct
import zipfile

try:
    from hashlib import md5 as md5
except ImportError:
    from md5 import md5

prog = os.path.basename(sys.argv[0])

video_files = [ 'asf', 'avi', 'divx', 'm2ts', 'mkv', 'mp4', 'mpeg', 'mpg', 'ogm', 'rm', 'rmvb', 'wmv' ]
languages = { 'pl': 'PL', 'en': 'ENG' }

def calculate_digest(filename):
    d = md5()
    try:
        d.update(open(filename, "rb").read(10485760))
    except (IOError, OSError), e:
        raise Exception('Hashing video file failed: %s' % ( e ))
    return d.hexdigest()

def napiprojekt_hash(z):
    idx = [ 0xe, 0x3,  0x6, 0x8, 0x2 ]
    mul = [   2,   2,    5,   4,   3 ]
    add = [   0, 0xd, 0x10, 0xb, 0x5 ]

    b = []
    for i in xrange(len(idx)):
        a = add[i]
        m = mul[i]
        i = idx[i]

        t = a + int(z[i], 16)
        v = int(z[t:t+2], 16)
        b.append( ("%x" % (v*m))[-1] )

    return ''.join(b)

def napisy24_hash(filename): 
    try: 
        longlongformat = '<q'  # little-endian long long
        bytesize = struct.calcsize(longlongformat)

        f = open(filename, "rb")

        filesize = os.path.getsize(filename)
        hash = filesize

        if filesize < 65536 * 2:
            raise Exception('Hashing (napisy24) video file failed: `%s\': File too small' % ( filename ))

        for x in range(65536/bytesize): 
            buffer = f.read(bytesize) 
            (l_value,)= struct.unpack(longlongformat, buffer)  
            hash += l_value 
            hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number  


        f.seek(max(0,filesize-65536),0) 
        for x in range(65536/bytesize): 
            buffer = f.read(bytesize) 
            (l_value,)= struct.unpack(longlongformat, buffer)  
            hash += l_value 
            hash = hash & 0xFFFFFFFFFFFFFFFF 

        f.close() 
        returnedhash =  "%016x" % hash 
        return returnedhash 

    except IOError, e:
        raise Exception('Hashing (napisy24) video file failed: %s' % ( e ))

def usage():
    print >> sys.stderr, "Usage: %s [OPTIONS]... [FILE|DIR]..." % prog
    print >> sys.stderr, "Find video files and download matching subtitles from napiprojekt/napisy24 server."
    print >> sys.stderr
    print >> sys.stderr, "Supported options:"
    print >> sys.stderr, "     -h, --help            display this help and exit"
    print >> sys.stderr, "     -l, --lang=LANG       subtitles language"
    print >> sys.stderr, "     -n, --nobackup        make no subtitle backup when in update mode"
    print >> sys.stderr, "     -c, --nocover         do not download cover images"
    print >> sys.stderr, "     -u, --update          fetch new and also update existing subtitles"
    print >> sys.stderr, "     -d, --dest=DIR        destination directory"
    print >> sys.stderr
    print >> sys.stderr, "Report bugs to <arekm@pld-linux.org>."

def get_desc_links(digest, file=None):
    # improve me
    re_link = re.compile(r'<a.*?href=[\'"](http://.*?)[ >\'"]', re.IGNORECASE)
    d = ""

    try:
        url = "http://www.napiprojekt.pl/index.php3?www=opis.php3&id=%s&film=%s" % (urllib2.quote(digest), urllib2.quote(file))
        f = urllib2.urlopen(url)
        d = f.read()
        f.close()
    except Exception, e:
        return False
    links = re_link.findall(d)
    ignore = [ r'.*dobreprogramy\.pl', r'.*napiprojekt\.pl.*', r'.*nokaut\.pl.*', r'.*rodisite\.com.*' ]
    for i in range(0, len(ignore)):
        ignore[i] = re.compile(ignore[i], re.IGNORECASE)
    ilinks = links[:]
    for l in ilinks:
        # main pages are useless
        if l.count('/') < 3:
            links.remove(l)
            continue
        # blacklisted sites
        for i in ignore:
            if i.match(l):
                links.remove(l)
    return links

def get_cover(digest):
    cover = ""
    try:
        url = "http://www.napiprojekt.pl/okladka_pobierz.php?id=%s&oceny=-1" % (urllib2.quote(digest))
        f = urllib2.urlopen(url)
        cover = f.read()
        f.close()
        content_type = f.info()['Content-Type']
        extension = mimetypes.guess_all_extensions(content_type)[-1]
    except Exception, e:
        return False
    return (cover, extension)

def get_subtitle_napisy24(filename, digest=False, lang="pl"):
    raise Exception('Subtitle NOT FOUND')

    url = "http://napisy24.pl/run/CheckSubAgent.php"

    pdata = []
    pdata.append(('postAction', 'CheckSub'))
    pdata.append(('ua', 'pynapi'))
    pdata.append(('ap', 'XaA!29OkF5Pe'))
    pdata.append(('nl', lang))
    pdata.append(('fn', filename))
    pdata.append(('fh', napisy24_hash(filename)))
    pdata.append(('fs', os.path.getsize(filename)))
    if digest:
        pdata.append(('md5', digest))

    repeat = 3
    error = "Fetching subtitle (napisy24) failed:"
    while repeat > 0:
        repeat = repeat - 1
        try:
            sub = urllib2.urlopen(url, data=urllib.urlencode(pdata))
            if hasattr(sub, 'getcode'):
                http_code = sub.getcode() 
            sub = sub.read()
        except (IOError, OSError), e:
            error = error + " %s" % (e)
            time.sleep(0.5)
            continue

        if http_code != 200:
            error = error + ",HTTP code: %s" % (str(http_code))
            time.sleep(0.5)
            continue

        err_add = ''
        if sub.startswith('OK-2|'):
            pos = sub.find('||')
            if pos >= 2 and len(sub) > (pos + 2):
                sub = sub[pos+2:]

                try:  
                    subzip=zipfile.ZipFile(StringIO.StringIO(sub))
                    sub=''
                    for name in subzip.namelist():
                        sub += subzip.read(name)
                except Exception, e:
                    raise Exception('Subtitle NOT FOUND%s' % e)
            else:
                raise Exception('Subtitle NOT FOUND (subtitle too short)')
        elif sub.startswith('OK-'):
            raise Exception('Subtitle NOT FOUND')
        else:
            raise Exception('Subtitle NOT FOUND (unknown error)')

        repeat = 0

    if sub is None or sub == "":
        raise Exception(error)

    return sub

def get_subtitle_napiprojekt(digest, lang="PL"):
    url = "http://napiprojekt.pl/unit_napisy/dl.php?l=%s&f=%s&t=%s&v=pynapi&kolejka=false&nick=&pass=&napios=%s" % \
        (lang, digest, napiprojekt_hash(digest), os.name)
    repeat = 3
    sub = None
    http_code = 200
    error = "Fetching subtitle (napiprojekt) failed:"
    while repeat > 0:
        repeat = repeat - 1
        try:
            sub = urllib2.urlopen(url)
            if hasattr(sub, 'getcode'):
                http_code = sub.getcode() 
            sub = sub.read()
        except (IOError, OSError), e:
            error = error + " %s" % (e)
            time.sleep(0.5)
            continue
    
        if http_code != 200:
            error = error + ",HTTP code: %s" % (str(http_code))
            time.sleep(0.5)
            continue
   
        err_add = ''
        if not sub.startswith('NPc'):
            err_add = " (unknown error)"
        if len(sub.split('\n')) < 20:
            raise Exception('Subtitle NOT FOUND%s' % err_add)
            
        repeat = 0

    if sub is None or sub == "":
        raise Exception(error)

    return sub

def main(argv=sys.argv):

    try:
        opts, args = getopt.getopt(argv[1:], "d:hl:nuc", ["dest", "help", "lang", "nobackup", "update", "nocover"])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        return 2

    output = None
    verbose = False
    nobackup = False
    nocover = False
    update = False
    lang = 'pl'
    dest = None
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-h", "--help"):
            usage()
            return 0
        elif o in ("-l", "--lang"):
            if a in languages:
                lang = a
            else:
                print >> sys.stderr, "%s: unsupported language `%s'. Supported languages: %s" % (prog, a, str(languages.keys()))
                return 1
        elif o in ("-n", "--nobackup"):
            nobackup = True
        elif o in ("-u", "--update"):
            update = True
        elif o in ("-c", "--nocover"):
            nocover = True
        elif o in ("-d", "--dest"):
            dest = a
        else:
            print >> sys.stderr, "%s: unhandled option" % prog
            return 1

    if not args:
        usage()
        return 2

    print >> sys.stderr, "%s: Subtitles language `%s'. Finding video files..." % (prog, lang)

    socket.setdefaulttimeout(180)

    files = []
    for arg in args:
        if os.path.isdir(arg):
            for dirpath, dirnames, filenames in os.walk(arg, topdown=False):
                for file in filenames:
                    if file[-4:-3] == '.' and file.lower()[-3:] in video_files:
                        files.append(os.path.join(dirpath, file))
        else:
            files.append(arg)

    files.sort()

    i_total = len(files)
    i = 0

    for file in files:
        i += 1

        vfile = file + '.txt'
        basefile = file
        if len(file) > 4:
            basefile = file[:-4]
            vfile = basefile + '.txt'
        if dest:
            vfile = os.path.join(dest, os.path.split(vfile)[1])

        if not update and os.path.exists(vfile):
            continue

        if not nobackup and os.path.exists(vfile):
            vfile_bak = vfile + '-bak'
            try:
                os.rename(vfile, vfile_bak)
            except (IOError, OSError), e:
                print >> sys.stderr, "%s: Skipping due to backup of `%s' as `%s' failure: %s" % (prog, vfile, vfile_bak, e)
                continue
            else:
                print >> sys.stderr, "%s: Old subtitle backed up as `%s'" % (prog, vfile_bak)

        print >> sys.stderr, "%s: %d/%d: Processing subtitle for %s" % (prog, i, i_total, file)

        try:
            digest = calculate_digest(file)
        except:
            print >> sys.stderr, "%s: %d/%d: %s" % (prog, i, i_total, sys.exc_info()[1])
            continue

        try:
            sub = get_subtitle_napiprojekt(digest, languages[lang])
        except:
            try:
                sub = get_subtitle_napisy24(file, digest, lang)
            except:
                print >> sys.stderr, "%s: %d/%d: %s" % (prog, i, i_total, sys.exc_info()[1])
                continue

        fp = open(vfile, 'wb')
        fp.write(sub)
        fp.close()
    
        desc = get_desc_links(digest, file)
        if desc:
            print >> sys.stderr, "%s: %d/%d: Description: " % (prog, i, i_total)
            for desc_i in desc:
                print >> sys.stderr, "\t\t%s" % desc_i
   
        cover_stored = ""
        if not nocover:
            cover_data = get_cover(digest)
            if cover_data:
                cover, extension = cover_data
                fp = open(basefile + extension, 'wb')
                fp.write(cover)
                fp.close()
                cover_stored = ", %s COVER STORED (%d bytes)" % (extension, len(cover))

        print >> sys.stderr, "%s: %d/%d: SUBTITLE STORED (%d bytes)%s" % (prog, i, i_total, len(sub), cover_stored)

    return 0

if __name__ == "__main__":
    ret = None
    try:
        ret = main()
    except (KeyboardInterrupt, SystemExit):
        print >> sys.stderr, "%s: Interrupted, aborting." % prog
    sys.exit(ret)
