"""Execute in RAM over CanMV USB; write only a fresh capture directory."""
import os
import time
import json
from media.media import MediaManager

print('K230_PREFLIGHT_BEGIN')
directory = '/sdcard/__SESSION__'
os.mkdir(directory)
stage = 'camera'
sensor = None
stream = None
audio = None
try:
    from media.sensor import Sensor
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(width=320, height=240)
    sensor.set_pixformat(Sensor.RGB565)
    MediaManager.init()
    sensor.run()
    time.sleep(2)
    for index in range(3):
        frame = sensor.snapshot()
        path = directory + '/camera_%02d.jpg' % index
        frame.save(path, quality=80)
        print('K230_CAPTURE=' + json.dumps({'kind': 'camera', 'file': path, 'width': frame.width(), 'height': frame.height()}))
        time.sleep_ms(200)
    sensor.stop()
    sensor = None
    MediaManager.deinit()
    stage = 'audio'
    from media.pyaudio import PyAudio, paInt16, RIGHT
    import media.wave as wave
    chunk = 1764
    audio = PyAudio()
    audio.initialize(chunk)
    MediaManager.init()
    stream = audio.open(format=paInt16, channels=2, rate=44100, input=True, frames_per_buffer=chunk)
    stream.volume(85, RIGHT)
    path = directory + '/microphone_stereo.wav'
    writer = wave.open(path, 'wb')
    writer.set_channels(2)
    writer.set_sampwidth(2)
    writer.set_framerate(44100)
    size = 0
    try:
        for index in range(75):
            data = stream.read()
            writer.write_frames(data)
            size += len(data)
    finally:
        writer.close()
    print('K230_CAPTURE=' + json.dumps({'kind': 'audio', 'file': path, 'pcm_bytes': size, 'rate': 44100, 'channels': 2, 'microphone_channel': 'right'}))
    stage = 'button'
    from machine import FPIOA, Pin
    fpioa = FPIOA()
    fpioa.set_function(21, FPIOA.GPIO21)
    key = Pin(21, Pin.IN, Pin.PULL_UP)
    print('K230_CAPTURE=' + json.dumps({'kind': 'button', 'gpio': 21, 'level': key.value()}))
except BaseException as error:
    print('K230_CAPTURE_ERROR=' + json.dumps({'stage': stage, 'type': type(error).__name__, 'message': str(error)}))
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
print('K230_PREFLIGHT_END')
