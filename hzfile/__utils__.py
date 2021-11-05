# coding: utf-8
################################################################################
# MIT License

# Copyright (c) 2020-2021 hrp/hrpzcf <hrpzcf@foxmail.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

from os import path
from pathlib import Path
from struct import calcsize, pack, unpack
from typing import Iterable

# 本平台各类型所占字节数
B = calcsize("B")
H = calcsize("H")
I = calcsize("I")
Q = calcsize("Q")

# 储存相关信息的数据类型及所占的空间大小(字节数)
# 类型信息见 struct 模块文档
HEADT, HEADN = "16B", B * 16  # 文件头(标识符)
TYPET, TYPEN = "4B", B * 4  # 类型长度表
FVERT, FVERN = "4H", H * 4  # 本文件格式版本
FCNTT, FCNTN = "I", I  # 合并的外部文件数
FSIZET, FSIZEN = "I", I  # 外部文件大小
FNLENT, FNLENN = "I", I  # 外部文件名长度(字节数)

BLANKBYTES = bytes(255)
CODING = "UTF-8"
HEADNUMS = 0, 104, 114, 112, 122, 99, 102
HEADBYTES = bytearray(16)
HEADBYTES[:7] = HEADNUMS
FVERNUMS = 0, 0, 1, 0
BOMSTART = HEADN + TYPEN + FVERN + 255 + FCNTN
# 类型长度表及文件格式版本的解析方式
REMHEADT = "<{}{}".format(TYPET, FVERT)
MAXFILESIZE = 2 ** (I * 8) - 1  # 外部最大文件大小


class HzFile(object):
    def __init__(self, hzfile):
        self.__hzpath = Path(hzfile)
        self.__head = list()
        self.__writable = 0
        self.__initialize()

    def __initialize(self):
        if self.__hzpath.exists():
            if self.__hzpath.is_file():
                self.__readhead()
            else:
                raise FileExistsError("Dir '{}' exists".format(self.__hzpath))
        else:
            self.__createhzfile()

    def fver(self):
        return self.__head[20:24]

    def fcnt(self):
        if len(self.__head) < 25:
            return 0
        return self.__head[24]  # [0,1,2,3]

    def fbom(self):
        fcount = self.fcnt()
        if not fcount:
            return list()
        filebom = list()
        with open(self.__hzpath, "rb") as hzb:
            hzb.seek(BOMSTART, 0)
            for i in range(fcount):
                fsize, fnlen = unpack(
                    "<{}{}".format(FSIZET, FNLENT), hzb.read(FSIZEN + FNLENN)
                )
                fname, *_ = unpack("{}s".format(fnlen), hzb.read(fnlen))
                filebom.append((fsize, fnlen, fname[:-1].decode(CODING)))
        return filebom

    def ftypesize(self, s=None):
        if s == "B":
            return self.__head[16]
        if s == "H":
            return self.__head[17]
        if s == "I":
            return self.__head[18]
        if s == "Q":
            return self.__head[19]
        if s is None:
            return self.__head[16:20]
        else:
            return calcsize(s)

    def __createhzfile(self):
        self.__head.extend(HEADNUMS)
        self.__head.extend([0] * (16 - len(HEADNUMS)))
        self.__head.extend((B, H, I, Q))
        self.__head.extend(FVERNUMS)
        with open(self.__hzpath, "wb") as hzb:
            hzb.write(HEADBYTES)
            hzb.write(pack(REMHEADT, B, H, I, Q, *FVERNUMS))
            hzb.write(BLANKBYTES)
        self.__writable = 1

    def __readhead(self):
        with open(self.__hzpath, "rb") as hzb:
            head = hzb.read(HEADN)
            if head != HEADBYTES:
                raise ValueError("This file is not a valid '.hz' file")
            self.__head.extend(unpack(HEADT, head))
            self.__head.extend(
                unpack("<{}{}".format(TYPET, FVERT), hzb.read(TYPEN + FVERN))
            )
            hzb.seek(HEADN + TYPEN + FVERN + 255, 0)
            fcntbytes = hzb.read(FCNTN)
            if fcntbytes:
                self.__head.extend(unpack(FCNTT, fcntbytes))
        return True

    def __writedata(self, bomlist, namelist):
        index, filesopened = 0, list()
        while index < len(namelist):
            try:
                f = namelist[index]
                filesopened.append(open(f, "rb"))
                index += 1
            except:
                del bomlist[index]
                del namelist[index]
        filenum = len(filesopened)
        with open(self.__hzpath, "ab") as hzb:
            self.__head.append(filenum)
            hzb.write(pack(FCNTT, filenum))
            hzb.write(b"".join(bomlist))
            for filehandle in filesopened:
                hzb.write(filehandle.read())
                filehandle.close()
        return True

    def merge(self, dirpath, recursion=False, bigok=False):
        if not self.__writable:
            raise IOError("It is read-only when opening written '.hz' file")
        self.__writable = 0
        dirpath = Path(dirpath)
        if not dirpath.is_dir():
            raise ValueError("Only the path to the directory is supported.")
        if recursion:
            pattern = "**/*"
        else:
            pattern = "*"
        bombytelist, filenamelist = list(), list()
        for i in dirpath.glob(pattern):
            if i.is_file():
                if i.samefile(self.__hzpath):
                    continue
                try:
                    filesize = i.stat().st_size
                except:
                    continue
                if filesize > MAXFILESIZE:
                    if bigok:
                        continue
                    raise Exception(
                        "The file cannot be larger than {} Byte.".format(MAXFILESIZE)
                    )
                filenamelist.append(i)
                namebyte = str(i.name).encode(CODING) + b"\x00"
                namelen = len(namebyte)
                bombytelist.append(
                    pack("<{}{}".format(FSIZET, FNLENT), filesize, namelen) + namebyte
                )
        self.__writedata(bombytelist, filenamelist)

    def extract(self, names, dirpath=None, overwrite=False):
        if not isinstance(names, Iterable):
            raise TypeError("The param1 must be an iterable object.")
        if dirpath is None:
            dirpath = Path.cwd()
        dirpath = Path(dirpath)
        if not dirpath.exists():
            dirpath.mkdir(parents=1)
        elif not dirpath.is_dir():
            raise ValueError("The param2 must be a path to a directory")
        names, namecount, bom = set(names), dict(), self.fbom()
        datastart = (
            HEADN
            + TYPEN
            + FVERN
            + 255
            + FCNTN
            + (FSIZEN + FNLENN) * len(bom)
            + sum(i[1] for i in bom)
        )
        hzbin = open(self.__hzpath, "rb")
        for i in bom:
            readlength, _, filename = i
            if filename in names:
                if filename in namecount:
                    namecount[filename] += 1
                else:
                    namecount[filename] = 0
                count = namecount[filename]
                if count > 0:
                    base, ext = path.splitext(filename)
                    filename = "{}({}){}".format(base, count, ext)
                filename = dirpath.joinpath(filename)
                if filename.exists():
                    if not overwrite:
                        continue
                    else:
                        if filename.is_dir():
                            filename.rmdir()
                with open(filename, "wb") as fbin:
                    hzbin.seek(datastart, 0)
                    fbin.write(hzbin.read(readlength))
            datastart += readlength
        hzbin.close()

    def extractall(self, dirpath=None, overwrite=False):
        names = (i[2] for i in self.fbom())
        self.extract(names, dirpath, overwrite)
