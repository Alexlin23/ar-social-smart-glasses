"""Download original OpenCV Zoo models with Git LFS SHA-256 verification."""
from __future__ import annotations

import argparse
import hashlib
import re
import urllib.request
from pathlib import Path

MODELS = (
    ('face_detection_yunet', 'face_detection_yunet_2023mar.onnx'),
    ('face_recognition_sface', 'face_recognition_sface_2021dec.onnx'),
)


def download_models(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for folder, filename in MODELS:
        relative = f'models/{folder}/{filename}'
        pointer_url = 'https://raw.githubusercontent.com/opencv/opencv_zoo/main/' + relative
        with urllib.request.urlopen(pointer_url, timeout=60) as response:
            pointer = response.read(4096).decode('ascii')
        match = re.search(r'oid sha256:([0-9a-f]{64})', pointer)
        if not match:
            raise RuntimeError(f'Cannot verify model hash: {filename}')
        expected = match.group(1)
        target = directory / filename
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() == expected:
                print(f'OK {filename}')
                continue
            raise FileExistsError(f'Model exists but hash differs: {target}. Move it aside before retrying.')
        # Exclusive file creation prevents overwriting another download or user file.
        temporary = directory / (filename + '.ar-download')
        try:
            with temporary.open('xb') as output:
                url = 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/' + relative
                digest = hashlib.sha256()
                with urllib.request.urlopen(url, timeout=120) as response:
                    while chunk := response.read(1024 * 1024):
                        digest.update(chunk)
                        output.write(chunk)
                if digest.hexdigest() != expected:
                    raise RuntimeError(f'Hash mismatch: {filename}')
            # Windows rename does not replace an existing destination.
            if target.exists():
                raise FileExistsError(str(target))
            temporary.rename(target)
        except FileExistsError:
            raise
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        print(f'Downloaded {filename} SHA256={expected}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent / 'models')
    download_models(parser.parse_args().directory)
