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

from os import path, remove
from pathlib import Path
from struct import calcsize, pack, unpack
from typing import Iterable

# 本平台各类型所占字节数
B = calcsize("B")  # unsigned char
H = calcsize("H")  # unsigned short
I = calcsize("I")  # unsigned int
Q = calcsize("Q")  # unsigned long long

# 储存相关信息的类型匹配符及所占的空间大小(字节数)
# 类型信息见 struct 模块文档
HEADF, HEADN = "16B", B * 16  # 文件头(标识符)
TYPEF, TYPEN = "4B", B * 4  # 类型长度表
FVERF, FVERN = "4H", H * 4  # 本文件格式版本
FCNTF, FCNTN = "I", I  # 合并的外部文件数
FSIZEF, FSIZEN = "I", I  # 外部文件大小
FNLENF, FNLENN = "I", I  # 外部文件名长度(字节数)

BLANKBYTES = bytes(255)
CODING = "UTF-8"
HEADNUMS = 0, 104, 114, 112, 122, 99, 102
HEADBYTES = bytearray(16)
HEADBYTES[:7] = HEADNUMS
FVERNUMS = 0, 0, 0, 1
# 类型长度表及文件格式版本的解析方式
REMHEADT = "<{}{}".format(TYPEF, FVERF)
# 外部最大文件大小
MAXFILESIZE = 2 ** (I * 8) - 1


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

    def __del__(self):
        if self.fcnt() == 0:
            try:
                remove(self.__hzpath)
            except:
                pass

    @property
    def FCNTN(self):
        """储存被合并文件数量的值的字节数"""
        return self.ftypesize("I")

    @property
    def FSIZEN(self):
        """储存单个被合并文件大小的值的字节数"""
        return self.ftypesize("I")

    @property
    def FNLENN(self):
        """储存单个被合并文件名长度的值的字节数"""
        return self.ftypesize("I")

    @property
    def FVERN(self):
        """储存生成'.hz'二进制文件所用的标准版本的值的字节数"""
        return self.ftypesize("H") * 4

    @property
    def BOMSTART(self):
        """被合并的文件信息表的起始位置的偏移量"""
        return HEADN + TYPEN + self.FVERN + 255 + self.FCNTN

    def fver(self):
        """返回本格式文件的版本信息列表[a,b,c,d]"""
        return self.__head[20:24]

    def fcnt(self):
        """返回被合并的文件总数量"""
        if len(self.__head) < 25:
            return 0
        return self.__head[24]  # [0,1,2,3]

    def fbom(self):
        """
        返回被合并的文件信息表
        [(文件大小， 文件名长度， 文件名), ...]
        """
        fcount = self.fcnt()
        if not fcount:
            return list()
        filebom = list()
        with fopen(self.__hzpath, "rb") as hzb:
            hzb.seek(self.BOMSTART, 0)
            for i in range(fcount):
                fsize, fnlen = unpack(
                    "<{}{}".format(FSIZEF, FNLENF), hzb.read(self.FSIZEN + self.FNLENN)
                )
                fnbytes = unpack("{}s".format(fnlen), hzb.read(fnlen))[0]
                filebom.append((fsize, fnlen, fnbytes[:-1].decode(CODING)))
        return filebom

    def ftypesize(self, s=None):
        """返回对应解析方式所需要的字节数"""
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
        with fopen(self.__hzpath, "wb") as hzb:
            hzb.write(HEADBYTES)
            hzb.write(pack(REMHEADT, B, H, I, Q, *FVERNUMS))
            hzb.write(BLANKBYTES)
        self.__writable = 1

    def __readhead(self):
        with fopen(self.__hzpath, "rb") as hzb:
            # 初次读取文件已存在的hz文件时，标识符表尚未生成，需按全局类型读取
            head = hzb.read(HEADN)
            if head != HEADBYTES:
                raise ValueError("This file is not a valid '.hz' file")
            self.__head.extend(unpack(HEADF, head))
            # 初次读取文件已存在的hz文件时，类型占用表尚未生成，需按全局类型读取
            self.__head.extend(unpack("<{}".format(TYPEF), hzb.read(TYPEN)))
            self.__head.extend(unpack("<{}".format(FVERF), hzb.read(self.FVERN)))
            hzb.seek(HEADN + TYPEN + self.FVERN + 255, 0)
            fcntbytes = hzb.read(self.FCNTN)
            if fcntbytes:
                self.__head.extend(unpack(FCNTF, fcntbytes))
        return True

    def __writedata(self, bomlist, namelist):
        index, filesopened = 0, list()
        while index < len(namelist):
            try:
                f = namelist[index]
                filesopened.append(fopen(f, "rb"))
                index += 1
            except:
                del bomlist[index]
                del namelist[index]
        filenum = len(filesopened)
        with fopen(self.__hzpath, "ab") as hzb:
            self.__head.append(filenum)
            hzb.write(pack(FCNTF, filenum))
            hzb.write(b"".join(bomlist))
            for filehandle in filesopened:
                hzb.write(filehandle.read())
                filehandle.close()
        return True

    def merge(self, dirpath, recursion=False, bigok=False):
        """
        将其他文件合并入'.hz'文件内

        参数 dirpath: str, 目录路径，里面包含的文件会被合并入'.hz'文件内
        参数 recursion: bool, 是否递归搜索本目录的子目录
        参数 bigok: bool，如果 bigok 为 True 则跳过超过大小的文件，否则抛出异常
        """
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
                        "The file cannot be larger than {} Byte".format(MAXFILESIZE)
                    )
                filenamelist.append(i)
                namebyte = str(i.name).encode(CODING) + b"\x00"
                namelen = len(namebyte)
                bombytelist.append(
                    pack("<{}{}".format(FSIZEF, FNLENF), filesize, namelen) + namebyte
                )
        self.__writedata(bombytelist, filenamelist)

    def extract(self, names, dirpath=None, overwrite=False):
        """
        从'.hz'文件中提取被合并的文件

        参数 name: Iterable，含有文件名的可迭代对象
        参数 dirpath: str, 为 None 将使用用当前工作目录
        参数 overwrite: bool, 当储存提取的文件的目录中有同名文件是否覆盖
        """
        if not isinstance(names, Iterable):
            raise TypeError("The param1 must be an iterable object.")
        if dirpath is None:
            dirpath = Path.cwd()
        else:
            dirpath = Path(dirpath)
            if not dirpath.exists():
                dirpath.mkdir(parents=1)
            elif not dirpath.is_dir():
                raise ValueError("The param2 must be a path to a directory")
        names, namecount, bom = set(names), dict(), self.fbom()
        datastart = (
            HEADN
            + TYPEN
            + self.FVERN
            + 255
            + self.FCNTN
            + (self.FSIZEN + self.FNLENN) * len(bom)
            + sum(i[1] for i in bom)
        )
        hzbin = fopen(self.__hzpath, "rb")
        for readlength, _, filename in bom:
            if filename in names:
                if filename in namecount:
                    namecount[filename] += 1
                else:
                    namecount[filename] = 0
                count = namecount[filename]
                if count > 0:
                    base, ext = path.splitext(filename)
                    filename = "{}_{}{}".format(base, count, ext)
                filename = dirpath.joinpath(filename)
                if filename.exists():
                    if not overwrite:
                        continue
                    else:
                        if filename.is_dir():
                            try:
                                filename.rmdir()
                            except:
                                continue
                with fopen(filename, "wb") as fbin:
                    hzbin.seek(datastart, 0)
                    fbin.write(hzbin.read(readlength))
            datastart += readlength
        hzbin.close()

    def extractall(self, dirpath=None, overwrite=False):
        """
        从'.hz'文件中提取所有被合并的文件

        参数同 extract 方法
        """
        names = (i[2] for i in self.fbom())
        self.extract(names, dirpath, overwrite)


def fopen(*args, **kwargs):
    """
    因 Python 3.5 的 open 函数第一个参数不支持Path对象

    所以此 fopen 函数作为 Python 3.5 的 open 函数兼容层
    """
    return open(str(args[0]), *args[1:], **kwargs)
