"""Optional real-model integration test using a supplied face image, in temporary data storage.

python tests_ar/real_model_smoke.py --image path/to/consented-test-image.jpg
"""
import argparse
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from face_pipeline import FaceRecognitionPipeline
from person_registration_service import PersonRegistrationService
from ar_hud.renderer import HudRenderer
from ar_hud.focus_manager import FocusManager
from ar_controls import ViewState


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--models-dir', type=Path, default=Path(__file__).resolve().parents[1]/'models')
    args = parser.parse_args()
    frame = cv2.imdecode(np.fromfile(args.image, np.uint8), cv2.IMREAD_COLOR)
    assert frame is not None, 'Cannot decode supplied image'
    with tempfile.TemporaryDirectory(prefix='ar-real-model-') as tmp:
        root = Path(tmp)
        pipeline = FaceRecognitionPipeline(
            args.models_dir/'face_detection_yunet_2023mar.onnx',
            args.models_dir/'face_recognition_sface_2021dec.onnx', root/'known_faces', root/'people')
        people = pipeline.process_frame(frame)
        assert people and not people[0].known, 'Expected an initially unregistered face'
        candidate = max(people, key=lambda p: p.bbox[2]*p.bbox[3])
        service = PersonRegistrationService(root/'people', root/'known_faces')
        result = service.register('模型联动测试', candidate.aligned_face, candidate.feature)
        pipeline.reload_indexes()
        pipeline.tracker.tracks.clear()
        people = pipeline.process_frame(frame)
        recognized = next(p for p in people if p.person_id == result.person_id)
        assert recognized.profile.display_name == '模型联动测试'
        assert recognized.score > 0.9, recognized.score
        selected = FocusManager().update([recognized], frame.shape[1], frame.shape[0], 1)
        hud = HudRenderer()
        rendered = hud.render(frame, [recognized], selected, ViewState(), '真实模型联动验证')
        assert rendered.shape == frame.shape
        assert hud.last_panels, 'No space for test HUD card'
        # A fresh pipeline must read back exactly the same original on-disk format.
        reloaded = FaceRecognitionPipeline(
            args.models_dir/'face_detection_yunet_2023mar.onnx',
            args.models_dir/'face_recognition_sface_2021dec.onnx', root/'known_faces', root/'people')
        assert any(p.person_id == result.person_id for p in reloaded.process_frame(frame))
        print(f'REAL MODEL PASS: detect -> unknown -> register -> reload -> recognize -> HUD -> restart; similarity={recognized.score:.4f}')


if __name__ == '__main__':
    main()
