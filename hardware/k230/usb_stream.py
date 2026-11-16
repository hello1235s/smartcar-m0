"""RAM-only simultaneous camera/audio/button stream over the CanMV debug USB."""
import os
import time
import json
import ubinascii
from media.sensor import Sensor
from media.media import MediaManager
from media.pyaudio import PyAudio, paInt16, RIGHT
from machine import FPIOA, Pin


def emit(kind, **values):
    values.update(kind=kind, board_ticks_ms=time.ticks_ms())
    print('SCUSB '+json.dumps(values))


sensor = audio = stream = None
try:
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(width=320, height=240)
    sensor.set_pixformat(Sensor.RGB565)
    chunk = 640
    audio = PyAudio()
    audio.initialize(chunk)
    MediaManager.init()
    stream = audio.open(format=paInt16, channels=2, rate=16000, input=True, frames_per_buffer=chunk)
    stream.volume(50, RIGHT)
    fpioa = FPIOA()
    fpioa.set_function(21, FPIOA.GPIO21)
    key = Pin(21, Pin.IN, Pin.PULL_UP)
    sensor.run()
    time.sleep(1)
    emit('ready', width=320, height=240, rate=16000, channels=2, sample_width=2)
    started = time.ticks_ms()
    last_frame = started
    seq = 0
    previous_key = key.value()
    while time.ticks_diff(time.ticks_ms(), started) < __DURATION_SECONDS__ * 1000:
        data = stream.read()
        emit('audio', seq=seq, data=ubinascii.b2a_base64(data).decode().strip())
        seq += 1
        current_key = key.value()
        if current_key != previous_key:
            time.sleep_ms(10)
            if key.value() == current_key:
                emit('button', pressed=current_key == 0)
                previous_key = current_key
        if time.ticks_diff(time.ticks_ms(), last_frame) >= 120:
            frame = sensor.snapshot()
            jpeg = frame.to_jpeg(quality=60)
            emit('video', seq=seq, width=320, height=240, data=ubinascii.b2a_base64(bytes(jpeg)).decode().strip())
            last_frame = time.ticks_ms()
        os.exitpoint()
except BaseException as error:
    emit('error', type=type(error).__name__, message=str(error))
finally:
    if sensor is not None:
        try:
            sensor.stop()
        except Exception:
            pass
    if stream is not None:
        stream.stop_stream()
        stream.close()
    if audio is not None:
        audio.terminate()
    try:
        MediaManager.deinit()
    except Exception:
        pass
emit('done')
