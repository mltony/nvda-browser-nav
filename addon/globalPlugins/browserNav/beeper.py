#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2021 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import api
import config
import ctypes
import functools
import math
import NVDAHelper
import nvwave
import operator
import os
import re
import speech
import struct
import threading
import tones
import ui
import wave

from . addonConfig import *
import logging
log = logging.getLogger(__name__)


# Cache NVDAHelper/localLib detection so it doesn't branch on every beep call
_cachedBeepFunc = None

def generateBeepWrapped(buffer, freq, duration, volLeft, volRight):
    global _cachedBeepFunc

    if _cachedBeepFunc:
        return _cachedBeepFunc(buffer, int(freq), int(duration), int(volLeft), int(volRight))

    try:

        # Preferred modern path
        if hasattr(NVDAHelper, "localLib"):
            lib = NVDAHelper.localLib
            if hasattr(lib, "generateBeep"):
                _cachedBeepFunc = lib.generateBeep
                return _cachedBeepFunc(buffer, freq, duration, volLeft, volRight)
            if hasattr(lib, "_nvdaControllerInternal_generateBeep"):
                _cachedBeepFunc = lib._nvdaControllerInternal_generateBeep
                return _cachedBeepFunc(buffer, freq, duration, volLeft, volRight)

        # Legacy NVDAHelper
        if hasattr(NVDAHelper, "generateBeep"):
            _cachedBeepFunc = NVDAHelper.generateBeep
            return _cachedBeepFunc(buffer, freq, duration, volLeft, volRight)

    except Exception as e:

    # Fallback only once
    def _fallback(buf, f, d, l, r):
        if buf is None:
            try:
                tones.beep(f, d)
            except:
                pass
        return 0

    _cachedBeepFunc = _fallback
    return _cachedBeepFunc(buffer, freq, duration, volLeft, volRight)

# ============================================================
#                     BEEPER CLASS
# ============================================================

class Beeper:
    BASE_FREQ = speech.IDT_BASE_FREQUENCY

    def getPitch(self, indent):
        return self.BASE_FREQ * 2 ** (indent / 24.0)  # 24 quarter tones per octave.

    BEEP_LEN = 10  # millis
    PAUSE_LEN = 5  # millis
    MAX_CRACKLE_LEN = 400  # millis
    MAX_BEEP_COUNT = 40  # Corresponds to ~500 paragraphs via log formula

    def __init__(self):
        try:
            outputDevice = config.conf["speech"]["outputDevice"]
        except KeyError:
            outputDevice = config.conf["audio"]["outputDevice"]

        self.player = nvwave.WavePlayer(
            channels=2,
            samplesPerSec=int(tones.SAMPLE_RATE),
            bitsPerSample=16,
            outputDevice=outputDevice,
            wantDucking=False,
            purpose=nvwave.AudioPurpose.SOUNDS,
        )

    # ------------------------------------------------------------

    def fancyCrackle(self, levels, volume, initialDelay=0):
        l = len(levels)
        coef = 10
        l = coef * math.log(1 + l / coef)
        l = int(round(l))
        levels = self.uniformSample(levels, min(l, self.MAX_BEEP_COUNT))

        beepLen = self.BEEP_LEN
        pauseLen = self.PAUSE_LEN

        # SIZE QUERIES → wrapper
        initialDelaySize = 0 if initialDelay == 0 else generateBeepWrapped(
            None, self.BASE_FREQ, initialDelay, 0, 0
        )
        pauseBufSize = generateBeepWrapped(None, self.BASE_FREQ, pauseLen, 0, 0)
        beepBufSizes = [
            generateBeepWrapped(None, self.getPitch(l), beepLen, volume, volume)
            for l in levels
        ]

        bufSize = initialDelaySize + sum(beepBufSizes) + len(levels) * pauseBufSize
        buf = ctypes.create_string_buffer(bufSize)
        bufPtr = 0

        bufPtr += initialDelaySize

        # BUFFER WRITES → wrapper
        for l in levels:
            bufPtr += generateBeepWrapped(
                ctypes.cast(ctypes.byref(buf, bufPtr), ctypes.POINTER(ctypes.c_char)),
                self.getPitch(l),
                beepLen,
                volume,
                volume,
            )
            bufPtr += pauseBufSize

        self.player.stop()
        threading.Thread(target=lambda: self.player.feed(buf.raw)).start()

    # ------------------------------------------------------------

    def simpleCrackle(self, n, volume, initialDelay=0):
        return self.fancyCrackle([0] * n, volume, initialDelay=initialDelay)

    # ------------------------------------------------------------

    NOTES = "A,B,H,C,C#,D,D#,E,F,F#,G,G#".split(",")
    NOTE_RE = re.compile("[A-H][#]?")
    BASE_FREQ = 220

    def getChordFrequencies(self, chord):
        prev = -1
        result = []
        for m in self.NOTE_RE.finditer(chord):
            s = m.group()
            i = self.NOTES.index(s)
            while i < prev:
                i += 12
            result.append(int(self.BASE_FREQ * (2 ** (i / 12.0))))
            prev = i
        return result

    # ------------------------------------------------------------

    def fancyBeep(self, chord, length, left=10, right=10):
        beepLen = length
        freqs = self.getChordFrequencies(chord)
        intSize = 8  # bytes

        # SIZE QUERIES via wrapper
        bufSize = max(
            [
                generateBeepWrapped(None, freq, beepLen, right, left)
                for freq in freqs
            ]
        )

        if bufSize % intSize != 0:
            bufSize += intSize
            bufSize -= (bufSize % intSize)

        self.player.stop()
        result = [0] * (bufSize // intSize)

        # BUFFER BUILDS via wrapper
        for freq in freqs:
            buf = ctypes.create_string_buffer(bufSize)
            generateBeepWrapped(buf, freq, beepLen, right, left)
            bytesArr = bytearray(buf)
            unpacked = struct.unpack("<%dQ" % (bufSize // intSize), bytesArr)
            result = map(operator.add, result, unpacked)

        maxInt = 1 << (8 * intSize)
        result = map(lambda x: x % maxInt, result)
        packed = struct.pack("<%dQ" % (bufSize // intSize), *result)

        threading.Thread(target=lambda: self.player.feed(packed)).start()

    # ------------------------------------------------------------

    def uniformSample(self, a, m):
        n = len(a)
        if n <= m:
            return a
        result = []
        for i in range(0, m * n, n):
            result.append(a[i // m])
        return result

    def stop(self):
        self.player.stop()


# ============================================================
#                       PUBLIC INTERFACE
# ============================================================

beeper = Beeper()


def endOfDocument(message):
    volume = getConfig("noNextTextChimeVolume")
    beeper.fancyBeep("HF", 100, volume, volume)
    if getConfig("noNextTextMessage"):
        ui.message(message)


def getSoundsPath():
    globalPluginPath = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    addonPath = os.path.split(globalPluginPath)[0]
    soundsPath = os.path.join(addonPath, "sounds")
    return soundsPath


@functools.lru_cache(maxsize=128)
def adjustVolume(bb, volume):
    n = len(bb) // 2
    format = f"<{n}h"
    unpacked = struct.unpack(format, bb)
    unpacked = [int(x * volume / 100) for x in unpacked]
    result = struct.pack(format, *unpacked)
    return result


spcFile = None
spcPlayer = None
spcBuf = None


def skippedParagraphChime():
    global spcFile, spcPlayer, spcBuf
    if spcPlayer is None:
        spcFile = wave.open(getSoundsPath() + "\\classic\\on.wav", "r")
        try:
            outputDevice = config.conf["speech"]["outputDevice"]
        except KeyError:
            outputDevice = config.conf["audio"]["outputDevice"]

        spcPlayer = nvwave.WavePlayer(
            channels=spcFile.getnchannels(),
            samplesPerSec=spcFile.getframerate(),
            bitsPerSample=spcFile.getsampwidth() * 8,
            outputDevice=outputDevice,
            wantDucking=False,
            purpose=nvwave.AudioPurpose.SOUNDS,
        )

        spcFile.rewind()
        spcFile.setpos(100 * spcFile.getframerate() // 1000)
        spcBuf = spcFile.readframes(spcFile.getnframes())

    def playSkipParagraphChime():
        spcPlayer.stop()
        spcPlayer.feed(
            adjustVolume(
                spcBuf,
                getConfig("skipChimeVolume")
            )
        )
        spcPlayer.idle()

    threading.Thread(target=playSkipParagraphChime).start()
