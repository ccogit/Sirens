"""PCM v1: 32 Byte Kopf, Stereo-Float32 LE; nur Standardbibliothek."""
import struct
from .contracts import invalid

HEADER = struct.Struct("<IIIIQHBBI")
VERSION = 1
MIN_FRAMES = 256
MAX_FRAMES = 2048

def validate_header(h):
    limits = {"protocol_version": (1, 1), "stream_id": (1, 2**32-1),
              "epoch": (0, 2**32-1), "seq": (0, 2**32-1),
              "start_frame": (0, 2**64-1), "nframes": (MIN_FRAMES, MAX_FRAMES),
              "channels": (2, 2), "flags": (0, 0), "sample_rate": (8000, 192000)}
    for key, (lo, hi) in limits.items():
        value = h.get(key)
        if type(value) is not int or not lo <= value <= hi:
            raise invalid(key)
    if h["start_frame"] + h["nframes"] > 2**64:
        raise invalid("start_frame")
    return h

FIELDS = ("protocol_version", "stream_id", "epoch", "seq", "start_frame",
          "nframes", "channels", "flags", "sample_rate")

def pack(header, payload):
    validate_header(header)
    if not isinstance(payload, (bytes, bytearray, memoryview)) or len(payload) != header["nframes"] * 8:
        raise invalid("payload")
    return HEADER.pack(*(header[k] for k in FIELDS)) + bytes(payload)

def unpack(block):
    if len(block) < HEADER.size:
        raise invalid("header")
    h = validate_header(dict(zip(FIELDS, HEADER.unpack_from(block))))
    if len(block) != HEADER.size + h["nframes"] * 8:
        raise invalid("payload")
    return h, bytes(block[HEADER.size:])
