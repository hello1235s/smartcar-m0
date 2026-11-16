"""Verify USB-copied image and microphone data; produce ASR-ready mono WAV."""
import argparse
import audioop
import hashlib
import json
import wave
from pathlib import Path

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    report = {'source': 'real_K230_USB_MTP', 'images': []}
    for path in sorted(args.directory.glob('camera_*.jpg')):
        image = cv2.imread(str(path))
        if image is None or image.shape != (240, 320, 3):
            raise RuntimeError('Invalid captured JPEG: ' + str(path))
        report['images'].append({'file': path.name, 'shape': list(image.shape), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    with wave.open(str(args.directory / 'microphone_stereo.wav'), 'rb') as source:
        params = source.getparams()
        pcm = source.readframes(params.nframes)
    assert params.nchannels == 2 and params.sampwidth == 2
    samples = np.frombuffer(pcm, dtype='<i2').reshape(-1, 2).astype(np.float64)
    rms = np.sqrt(np.mean(samples ** 2, axis=0))
    mono = audioop.tomono(pcm, 2, 0, 1)
    resampled, _ = audioop.ratecv(mono, 2, 1, params.framerate, 16000, None)
    with wave.open(str(args.directory / 'microphone_right_16k.wav'), 'wb') as target:
        target.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        target.writeframes(resampled)
    report['audio'] = {'duration_s': params.nframes / params.framerate, 'rate': params.framerate, 'left_rms': float(rms[0]), 'right_rms': float(rms[1]), 'right_peak': int(np.max(np.abs(samples[:, 1]))), 'right_nonzero_fraction': float(np.mean(samples[:, 1] != 0)), 'asr_file': 'microphone_right_16k.wav'}
    report['checks'] = {'camera_readable': len(report['images']) >= 3, 'microphone_has_signal': bool(rms[1] > 0), 'voice_command_validation': 'pending_spoken_commands'}
    (args.directory / 'capture_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
