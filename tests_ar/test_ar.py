"""Run from repository root: python -m unittest discover -s tests_ar -v."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from ar_controls import Action, ViewState, action_for_key
from ar_hud.focus_manager import FocusManager
from ar_hud.layout import intersects, place_panel, safe_area
from ar_hud.renderer import HudRenderer
from person_registration_service import PersonRegistrationService
from person_memory import PersonMemoryStore
from face_identity_store import FaceIdentityStore
from run_ar_view import demo_frame, main, parse_args


class FocusTests(unittest.TestCase):
    def setUp(self):
        self.people = demo_frame(1280, 720, 0)[1]
        self.focus = FocusManager()

    def test_center_selection_stays_until_lost(self):
        self.assertEqual(self.focus.update(self.people, 1280, 720, 1).track_id, 2)
        self.focus.cycle(self.people, 2)
        self.assertEqual(self.focus.update(self.people, 1280, 720, 3).track_id, 3)

    def test_disappearance_does_not_show_stale_card(self):
        self.focus.update(self.people, 1280, 720, 1)
        others = [self.people[0], self.people[2]]
        self.assertIsNone(self.focus.update(others, 1280, 720, 1.1))
        self.assertIsNotNone(self.focus.update(others, 1280, 720, 2))

    def test_cycle_wrap_and_empty(self):
        self.focus.update(self.people, 1280, 720, 1)
        self.assertEqual(self.focus.cycle(self.people, 2, -1).track_id, 1)
        self.assertEqual(self.focus.cycle(self.people, 3, -1).track_id, 3)
        self.assertIsNone(self.focus.cycle([], 4))


class LayoutAndViewTests(unittest.TestCase):
    def setUp(self):
        self.renderer = HudRenderer()

    def test_no_room_omits_card(self):
        self.assertIsNone(place_panel((100, 60), (0, 0, 1, 1), (0, 0, 320, 240), [(0, 0, 320, 240)]))

    def test_card_bounds_and_no_overlap(self):
        for width, height in ((320, 240), (640, 480), (1280, 720), (1920, 1080)):
            for size in (16, 22, 40):
                with self.subTest(width=width, font=size):
                    frame, people = demo_frame(width, height, 0)
                    original = frame.copy()
                    state = ViewState(expanded=True, font_size=size)
                    output = self.renderer.render(frame, people, people[1], state)
                    self.assertEqual(frame.shape, output.shape)
                    np.testing.assert_array_equal(original, frame)
                    panels = self.renderer.last_panels
                    sx, sy, sw, sh = safe_area(width, height, 24, size+22, size+26)
                    for index, rect in enumerate(panels):
                        x, y, w, h = rect
                        self.assertTrue(sx <= x and sy <= y and x+w <= sx+sw and y+h <= sy+sh)
                        self.assertFalse(any(intersects(rect, p.bbox) for p in people))
                        self.assertFalse(any(intersects(rect, other) for other in panels[index+1:]))

    def test_hide_and_pause_remove_all_person_cards(self):
        frame, people = demo_frame(1280, 720, 0)
        for state in (ViewState(hidden=True), ViewState(paused=True)):
            self.renderer.render(frame, people, people[1], state)
            self.assertEqual(self.renderer.last_panels, [])

    def test_expansion_changes_output_and_text_fits(self):
        frame, people = demo_frame(1280, 720, 0)
        compact = self.renderer.render(frame, people, people[1], ViewState())
        expanded = self.renderer.render(frame, people, people[1], ViewState(expanded=True))
        self.assertFalse(np.array_equal(compact, expanded))
        text = self.renderer.fit('中文长名字' * 50, 150, 22)
        self.assertLessEqual(self.renderer.font(22).getlength(text), 150)

    def test_actions_and_font_limits(self):
        state = ViewState()
        self.assertEqual(action_for_key(ord('H')), Action.HIDE)
        self.assertEqual(action_for_key(-1), Action.NONE)
        state.apply(Action.EXPAND)
        self.assertTrue(state.expanded)
        state.apply(Action.PAUSE)
        self.assertTrue(state.paused)
        self.assertFalse(state.expanded)
        for _ in range(50):
            state.apply(Action.LARGER)
        self.assertEqual(state.font_size, 40)
        for _ in range(50):
            state.apply(Action.SMALLER)
        self.assertEqual(state.font_size, 16)


class OriginalLibraryIntegrationTests(unittest.TestCase):
    def test_registration_files_and_reload_original_store(self):
        with tempfile.TemporaryDirectory(prefix='ar-test-') as tmp:
            people, cache = Path(tmp)/'people', Path(tmp)/'known_faces'
            service = PersonRegistrationService(people, cache)
            feature = np.ones((1, 128), np.float32)
            image = np.zeros((112, 112, 3), np.uint8)
            result = service.register('联动测试', image, feature, relationship='friend')
            store = PersonMemoryStore(people)
            store.load()
            self.assertEqual(store.get_by_person_id(result.person_id).display_name, '联动测试')
            loaded = FaceIdentityStore(people, cache).load_feature_index(store)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].person_id, result.person_id)
            np.testing.assert_array_equal(loaded[0].feature, feature)
            service.add_face_sample(result.person_id, image, feature)
            self.assertEqual(len(FaceIdentityStore(people, cache).load_feature_index(store)), 2)

    def test_model_demo_and_headless_snapshot(self):
        with tempfile.TemporaryDirectory(prefix='ar-test-') as tmp:
            output = Path(tmp)/'demo.png'
            self.assertEqual(main(['--demo', '--headless', '--frames', '3', '--snapshot', str(output)]), 0)
            self.assertIsNotNone(cv2.imread(str(output)))

    def test_missing_model_is_actionable_error(self):
        with tempfile.TemporaryDirectory(prefix='ar-test-') as tmp:
            self.assertEqual(main(['--check', '--models-dir', tmp]), 2)

    def test_invalid_args_rejected(self):
        for args in (['--headless'], ['--threshold', '2'], ['--width', '0']):
            with self.assertRaises(SystemExit):
                parse_args(args)

    def test_capture_released_when_processing_fails(self):
        class Capture:
            released = False
            def get(self, _): return 30
            def read(self): return True, np.zeros((480, 640, 3), np.uint8)
            def release(self): self.released = True
        capture = Capture()
        with tempfile.TemporaryDirectory(prefix='ar-test-') as tmp:
            for filename in ('face_detection_yunet_2023mar.onnx', 'face_recognition_sface_2021dec.onnx'):
                (Path(tmp)/filename).touch()
            with patch('run_ar_view.open_source', return_value=(capture, True)), \
                 patch('face_pipeline.FaceRecognitionPipeline') as factory:
                factory.return_value.process_frame.side_effect = RuntimeError('injected frame failure')
                self.assertEqual(main(['--headless', '--frames', '2', '--data-dir', tmp,
                                       '--models-dir', tmp]), 2)
        self.assertTrue(capture.released)

    def test_original_terminal_registration_flow(self):
        from face_pipeline import FaceRecognitionPipeline
        from recognize_face import register_unknown_person
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory(prefix='ar-test-') as tmp:
            root = Path(tmp)
            service = PersonRegistrationService(root/'people', root/'known_faces')
            pipeline = Mock(spec=FaceRecognitionPipeline)
            pipeline.memory_store = PersonMemoryStore(root/'people')
            pipeline.reload_indexes.side_effect = pipeline.memory_store.load
            person = demo_frame(1280, 720, 0)[1][0]
            with patch('builtins.input', side_effect=['终端登记测试', 'friend', '', '', '']):
                register_unknown_person(person, service, pipeline)
            self.assertEqual(len(pipeline.memory_store.profiles_by_id), 1)
            # Same-name choice adds a sample to the existing person, not a duplicate.
            with patch('builtins.input', side_effect=['终端登记测试', '1']):
                register_unknown_person(person, service, pipeline)
            self.assertEqual(len(pipeline.memory_store.profiles_by_id), 1)
            self.assertEqual(len(list((root/'known_faces').glob('*.npy'))), 2)


if __name__ == '__main__':
    unittest.main()
