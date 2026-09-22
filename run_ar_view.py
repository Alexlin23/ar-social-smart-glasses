"""AR HUD entry point. Existing project modules remain the source of identity data."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
WINDOW = 'AR Social Glasses HUD'


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='AR HUD: camera, video, or clearly labelled synthetic demo.')
    parser.add_argument('--source', default='0', help='Camera index or video path relative to project root')
    parser.add_argument('--demo', action='store_true', help='Synthetic UI demo: no camera or models')
    parser.add_argument('--headless', action='store_true', help='Run without opening a window; requires --frames')
    parser.add_argument('--frames', type=int, default=0, help='Exit after N frames, 0 means unlimited GUI')
    parser.add_argument('--snapshot', type=Path, help='Save last rendered frame (only when explicitly requested)')
    parser.add_argument('--loop', action='store_true', help='Loop a video file and reset tracking at each rewind')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--font', type=Path, help='Chinese TTF/OTF/TTC font')
    parser.add_argument('--font-size', type=int, default=22)
    parser.add_argument('--margin', type=int, default=24, help='Safe-area margin in source-frame pixels')
    parser.add_argument('--threshold', type=float, default=0.45)
    parser.add_argument('--stale-seconds', type=float, default=1.5)
    parser.add_argument('--data-dir', type=Path, default=ROOT, help='Root containing people/ and known_faces/')
    parser.add_argument('--models-dir', type=Path, default=ROOT / 'models')
    parser.add_argument('--check', action='store_true', help='Check imports, font and real ONNX loading without camera access')
    args = parser.parse_args(argv)
    if args.width < 320 or args.height < 240:
        parser.error('Requested resolution must be at least 320 x 240')
    if not 16 <= args.font_size <= 40 or not 0 <= args.margin <= 100:
        parser.error('font-size must be 16..40 and margin 0..100')
    if not -1 <= args.threshold <= 1 or not 0 < args.stale_seconds < 60:
        parser.error('threshold must be -1..1 and stale-seconds must be >0 and <60')
    if args.frames < 0 or (args.headless and not args.check and args.frames < 1):
        parser.error('--headless requires a positive --frames value')
    for attr in ('models_dir', 'data_dir', 'font', 'snapshot'):
        path = getattr(args, attr)
        if path is not None and not path.is_absolute():
            setattr(args, attr, ROOT / path)
    return args


def open_source(source, width, height):
    import cv2
    if source.isdecimal():
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform == 'win32' else [cv2.CAP_ANY]
        for backend in backends:
            cap = cv2.VideoCapture(int(source), backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                return cap, True
            cap.release()
        raise RuntimeError(f'Cannot open camera {source}; close other camera apps or try --source 1.')
    path = Path(source)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(f'Video does not exist: {path}')
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f'Cannot decode video: {path}')
    return cap, False


def demo_frame(width, height, index):
    """Actual original result/profile types, but visibly synthetic people."""
    import cv2
    import numpy as np
    from face_pipeline import RecognizedPerson
    from person_memory import PersonProfile
    frame = np.full((height, width, 3), (35, 30, 24), np.uint8)
    people = []
    for i, fraction in enumerate((0.24, 0.58, 0.82)):
        x, y, w, h = int(width*fraction)-40, int(height*0.34), 80, 105
        cv2.ellipse(frame, (x+w//2, y+h//2), (w//2, h//2), 0, 0, 360, (90, 100, 110), -1)
        profile = PersonProfile('demo_1', '演示人物 小林', '朋友', Path('demo-only'), {},
                                {'兴趣与偏好': '摄影、徒步', '承诺与待办': '下次带上摄影作品',
                                 '当前状态': '准备周末出游'}) if i == 1 else None
        people.append(RecognizedPerson(i+1, (x, y, w, h), 'demo_1' if profile else None,
                      None, 0.8 if profile else -1.0, profile,
                      np.zeros((112, 112, 3), np.uint8), np.zeros((1, 128), np.float32)))
    return frame, people


def main(argv=None):
    args = parse_args(argv)
    try:
        import cv2
        import numpy as np
        from face_pipeline import FaceRecognitionPipeline
        from person_registration_service import PersonRegistrationService
        from recognize_face import register_unknown_person
        from ar_controls import Action, ViewState, action_for_key
        from ar_hud.focus_manager import FocusManager
        from ar_hud.renderer import HudRenderer
        from window_ui import create_adaptive_window, get_window_size, is_window_closed, resize_with_letterbox
    except ImportError as error:
        print(f'Missing dependency: {error}. Install: python -m pip install -r requirements-ar.txt', file=sys.stderr)
        return 2

    cap = None
    window_created = False
    rendered = None
    try:
        renderer = HudRenderer(args.font, args.margin)
        detector = args.models_dir / 'face_detection_yunet_2023mar.onnx'
        recognizer = args.models_dir / 'face_recognition_sface_2021dec.onnx'
        if not args.demo:
            for model in (detector, recognizer):
                if not model.is_file():
                    raise FileNotFoundError(f'Missing {model}; run python ar_setup_models.py')
        if args.check:
            if not args.demo:
                cv2.FaceDetectorYN.create(str(detector), '', (320, 320))
                cv2.FaceRecognizerSF.create(str(recognizer), '')
            print(f'CHECK OK: original modules, OpenCV {cv2.__version__}, Chinese font'
                  + (', ONNX models' if not args.demo else ' (demo, models not checked)'))
            return 0

        pipeline = None
        registration = None
        is_camera = False
        if not args.demo:
            pipeline = FaceRecognitionPipeline(detector, recognizer,
                args.data_dir / 'known_faces', args.data_dir / 'people', args.threshold)
            registration = PersonRegistrationService(args.data_dir / 'people', args.data_dir / 'known_faces')
            cap, is_camera = open_source(args.source, args.width, args.height)
        state = ViewState(font_size=args.font_size)
        focus = FocusManager()
        count = 0
        fps = 0.0
        stream_fps = cap.get(cv2.CAP_PROP_FPS) if cap and not is_camera else 30.0
        period = 1 / stream_fps if 0 < stream_fps <= 240 else 1 / 30
        print('N/Tab next | B previous | E/Enter expand | H hide | SPACE pause recognition | C contrast | +/- text | R register | Q exit')
        while True:
            started = time.perf_counter()
            if args.demo:
                frame, people = demo_frame(args.width, args.height, count)
                if state.paused:
                    people = []
            else:
                ok, frame = cap.read()
                if not ok:
                    focus.clear()
                    if args.loop and not is_camera and count:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        pipeline.tracker.tracks.clear()
                        ok, frame = cap.read()
                    if not ok:
                        if is_camera or count == 0:
                            raise RuntimeError('Video input lost or first frame cannot be decoded.')
                        break
                people = [] if state.paused else pipeline.process_frame(frame)
            now = time.perf_counter()
            stale = now - started > args.stale_seconds
            if stale:
                people = []
                focus.clear()
            previous_id = focus.track_id
            selected = focus.update(people, frame.shape[1], frame.shape[0], now)
            if selected is None or previous_id != focus.track_id:
                state.expanded = False
            status = '模拟演示 · 非真实识别' if args.demo else f'实时摄像头 · {fps:.0f} FPS' if is_camera else f'视频回放 · {fps:.0f} FPS'
            if stale:
                status += ' | 处理超时，人物提示已清除'
            rendered = renderer.render(frame, people, selected, state, status)
            count += 1
            if not args.headless:
                if not window_created:
                    create_adaptive_window(WINDOW, frame.shape[1], frame.shape[0])
                    window_created = True
                ww, wh = get_window_size(WINDOW, frame.shape[1], frame.shape[0])
                cv2.imshow(WINDOW, resize_with_letterbox(rendered, ww, wh))
            if args.frames and count >= args.frames:
                break
            if args.headless:
                action = Action.NONE
            else:
                remaining = max(1, int(1000 * (period - (time.perf_counter() - started))))
                action = action_for_key(cv2.waitKeyEx(min(remaining, 100)))
                if is_window_closed(WINDOW):
                    break
            if action == Action.QUIT:
                break
            if action in (Action.NEXT, Action.PREVIOUS):
                focus.cycle(people, now, 1 if action == Action.NEXT else -1)
                state.expanded = False
            elif action == Action.REGISTER:
                if args.demo:
                    print('Demo registration is disabled. Use a real camera or video source.')
                elif selected is None or selected.known or state.paused or state.hidden:
                    print('Select a visible unknown person while recognition and HUD are active.')
                else:
                    # Reuse the exact original registration flow (including same-name handling).
                    # Clear personal overlays before terminal interaction.
                    state.paused = True
                    cv2.imshow(WINDOW, renderer.render(frame, [], None, state,
                        '请在终端输入登记信息；姓名留空取消'))
                    cv2.waitKey(1)
                    try:
                        register_unknown_person(selected, registration, pipeline)
                    except (Exception, KeyboardInterrupt) as error:
                        print(f'Registration cancelled/failed: {error}')
                    # Camera buffers may contain old frames after terminal interaction.
                    if is_camera:
                        cap.release()
                        cap, is_camera = open_source(args.source, args.width, args.height)
                    pipeline.tracker.tracks.clear()
                    focus.clear()
                    state.paused = False
            else:
                state.apply(action)
                if action == Action.PAUSE:
                    focus.clear()
                    if pipeline:
                        pipeline.tracker.tracks.clear()
            elapsed = max(time.perf_counter() - started, 1e-6)
            fps = 1/elapsed if fps == 0 else fps*0.9 + 0.1/elapsed
        if args.snapshot and rendered is not None:
            args.snapshot.parent.mkdir(parents=True, exist_ok=True)
            # Unicode-safe Windows file output.
            ok, encoded = cv2.imencode('.png', rendered)
            if not ok:
                raise RuntimeError('Snapshot encoding failed')
            with args.snapshot.open('xb') as output:
                output.write(encoded.tobytes())
        print(f'RUN OK: {count} frames processed')
        return 0
    except (OSError, ValueError, RuntimeError, cv2.error) as error:
        print(f'AR startup/runtime error: {error}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    finally:
        if cap is not None:
            cap.release()
        if window_created:
            cv2.destroyAllWindows()


if __name__ == '__main__':
    sys.exit(main())
