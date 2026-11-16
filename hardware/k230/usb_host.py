"""Windows USB owner and bounded localhost relay. No K230 Wi-Fi or firmware changes."""
import argparse
import audioop
import base64
import json
import queue
import socket
import struct
import threading
import time
import wave
from pathlib import Path
import serial


class CanMV:
    def __init__(self, port):
        self.serial = serial.Serial(port=None, baudrate=115200, timeout=8, write_timeout=5)
        self.serial.port = port
        self.serial.rts, self.serial.dtr = True, False
        self.serial.open()
        time.sleep(0.05)
        self.serial.dtr = True
        time.sleep(0.3)
        self.serial.reset_input_buffer()
        self.synchronize()

    def header(self, command, length=0):
        self.serial.write(struct.pack('<BBI', 0x30, command, length))

    def read(self, length):
        data = bytearray()
        while len(data) < length:
            chunk = self.serial.read(length-len(data))
            if not chunk:
                raise TimeoutError('CanMV USB response timed out')
            data.extend(chunk)
        return bytes(data)

    def synchronize(self):
        self.header(0x8D, 4)
        window = bytearray()
        deadline = time.monotonic()+12
        while time.monotonic() < deadline:
            window.extend(self.read(1))
            if window[-4:] == b'\xaa\xbb\xee\xff':
                return
            if len(window) > 131072:
                break
        raise RuntimeError('Cannot synchronize CanMV USB')

    def query(self, command, length):
        self.header(command, length)
        return self.read(length)

    def stop(self):
        self.header(0x06)
        time.sleep(5.5)
        self.synchronize()
        deadline = time.monotonic()+12
        while struct.unpack('<I', self.query(0x87, 4))[0]:
            if time.monotonic() > deadline:
                raise RuntimeError('Original program did not stop')
            time.sleep(0.1)
        self.stdout()

    def execute(self, code):
        payload = (code+'\n').encode('utf-8')
        if len(payload) % 64 == 0:
            payload += b'\n'
        self.header(0x05, len(payload))
        time.sleep(0.5)
        self.serial.write(payload)
        time.sleep(0.5)

    def stdout(self):
        length = struct.unpack('<I', self.query(0x8E, 4))[0]
        if length > 131072:
            raise RuntimeError('Invalid CanMV output length')
        return self.query(0x8F, length) if length else b''

    def close(self):
        self.serial.close()


class Relay:
    def __init__(self, port):
        self.clients, self.lock = [], threading.Lock()
        self.workers=[]
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('127.0.0.1', port))
        self.server.listen(4)
        self.server.settimeout(0.2)
        self.closed = threading.Event()
        self.dropped = 0
        self.thread = threading.Thread(target=self.accept, daemon=True)
        self.thread.start()

    def accept(self):
        while not self.closed.is_set():
            try:
                client, _ = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            pending = queue.Queue(maxsize=128)
            with self.lock:
                self.clients.append(pending)
            worker=threading.Thread(target=self.send,args=(client,pending))
            self.workers.append(worker); worker.start()

    def send(self, client, pending):
        client.settimeout(1)
        try:
            while not self.closed.is_set() or not pending.empty():
                try:
                    payload = pending.get(timeout=0.2)
                except queue.Empty:
                    continue
                client.sendall(payload)
        except OSError:
            pass
        finally:
            client.close()
            with self.lock:
                self.clients.remove(pending)

    def publish(self, event):
        payload = (json.dumps(event)+'\n').encode()
        with self.lock:
            for pending in self.clients:
                try:
                    pending.put_nowait(payload)
                except queue.Full:
                    pending.get_nowait()
                    pending.put_nowait(payload)
                    self.dropped += 1

    def close(self):
        self.closed.set()
        self.server.close()
        self.thread.join(2)
        for worker in self.workers: worker.join(3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', default='COM3')
    parser.add_argument('--tcp-port', type=int, default=8766)
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    relay = Relay(args.tcp_port)
    device = CanMV(args.port)
    stats = dict(video=0, audio=0, audio_bytes=0, button=0, errors=[], source='real_K230_USB', start_wall_ns=time.time_ns())
    writer = wave.open(str(out/'microphone_right_16k.wav'), 'wb')
    writer.setparams((1,2,16000,0,'NONE','not compressed'))
    events = (out/'events.jsonl').open('w', encoding='utf-8')
    try:
        device.stop()
        code = (Path(__file__).with_name('usb_stream.py')).read_text(encoding='utf-8').replace('__DURATION_SECONDS__', str(args.seconds))
        device.execute(code)
        deadline = time.monotonic()+args.seconds+20
        buffer = b''
        first_video = last_video = None
        done = False
        while time.monotonic() < deadline and not done:
            buffer += device.stdout()
            if len(buffer) > 1048576:
                raise RuntimeError('USB framing buffer exceeded limit')
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                if not line.startswith(b'SCUSB '):
                    continue
                event = json.loads(line[6:])
                event['host_wall_ns'] = time.time_ns()
                kind = event['kind']
                if kind == 'video':
                    stats['video'] += 1
                    first_video = first_video or time.monotonic()
                    last_video = time.monotonic()
                    if stats['video'] <= 120:
                        (out/('frame_%04d.jpg' % stats['video'])).write_bytes(base64.b64decode(event['data']))
                elif kind == 'audio':
                    data = audioop.tomono(base64.b64decode(event['data']), 2, 0, 1)
                    writer.writeframesraw(data)
                    stats['audio'] += 1
                    stats['audio_bytes'] += len(data)
                elif kind == 'button':
                    stats['button'] += 1
                elif kind == 'error':
                    stats['errors'].append(event)
                elif kind == 'done':
                    done = True
                relay.publish(event)
                events.write(json.dumps({key:value for key,value in event.items() if key != 'data'})+'\n')
            time.sleep(0.005)
        stats['video_hz'] = (stats['video']-1)/(last_video-first_video) if stats['video'] > 1 else 0
        stats['audio_seconds'] = stats['audio_bytes']/32000
        stats['completed'] = done
        stats['relay_drops'] = relay.dropped
    finally:
        writer.close()
        events.close()
        relay.close()
        device.close()
        (out/'usb_report.json').write_text(json.dumps(stats, indent=2), encoding='utf-8')
    print(json.dumps(stats, indent=2))
    if stats['errors'] or not stats.get('completed') or not stats['video'] or not stats['audio']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
