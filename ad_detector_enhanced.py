"""
Enhanced AdDetector with machine learning-based recognition
and adaptive behavior based on results for the 2248 bot project
"""
import cv2
import numpy as np
import constants as const
from constants import EVENT_DEV, AD_BTN_X, AD_BTN_Y
from learning_engine import LearningEngine


def send_tap_like_mouse(adb_cmd, x, y, pressure=1024):
    """
    Tap в формате, как даёт эмулятор:
    TRACKING_ID -> POSITION_X/Y -> PRESSURE -> SYN
    потом PRESSURE=0 -> TRACKING_ID=-1 -> SYN
    """
    script_lines = [
        # палец вниз
        f"sendevent {EVENT_DEV} 3 57 0",
        f"sendevent {EVENT_DEV} 3 53 {x}",
        f"sendevent {EVENT_DEV} 3 54 {y}",
        f"sendevent {EVENT_DEV} 3 58 {pressure}",
        f"sendevent {EVENT_DEV} 0 0 0",
        # палец вверх
        f"sendevent {EVENT_DEV} 3 58 0",
        f"sendevent {EVENT_DEV} 3 57 -1",
        f"sendevent {EVENT_DEV} 0 0 0",
    ]

    cmd = 'adb shell "' + "; ".join(script_lines) + '"'
    return adb_cmd(cmd)


class EnhancedEndGameAdDetector2248:
    """
    Enhanced detector for 'no moves / watch ad' popup in 2248 with ML capabilities.
    Works with screenshot (BGR OpenCV image) and:
      - searches for button template in area of interest;
      - uses fallback coordinates from constants if template not found;
      - adapts behavior based on previous successful/unsuccessful attempts.
    """

    def __init__(self):
        # button template
        self.button_template = None
        self.button_threshold = 0.75
        
        # Machine learning component for adaptive behavior
        self.learning_engine = LearningEngine()
        self.attempt_history = []
        self.success_rate = 0.0

        # area of interest (x1, y1, x2, y2) where popup usually appears
        self.roi = None  # (x1, y1, x2, y2)

        # fallback coordinates (default from constants)
        if hasattr(const, "AD_BTN_X") and hasattr(const, "AD_BTN_Y"):
            self.fallback_btn = (int(const.AD_BTN_X), int(const.AD_BTN_Y))
        else:
            self.fallback_btn = None

        self.use_fallback_if_not_found = True
        
        # Adaptive threshold based on previous results
        self.adaptive_threshold = self.button_threshold

    def set_roi(self, img_shape, roi_rel=(0.1, 0.2, 0.9, 0.8)):
        """
        Configure area of interest relative to screen size.
        roi_rel = (left, top, right, bottom) in fractions.
        """
        h, w = img_shape[:2]
        x1 = int(w * roi_rel[0])
        y1 = int(h * roi_rel[1])
        x2 = int(w * roi_rel[2])
        y2 = int(h * roi_rel[3])
        self.roi = (x1, y1, x2, y2)

    def load_button_template(self, path):
        """
        Load button template 'Watch ad / Continue' from file.
        Need a pre-cut button fragment.
        """
        tmpl = cv2.imread(path)
        if tmpl is None:
            print(f"❌ Не удалось загрузить шаблон кнопки: {path}")
            return False
        self.button_template = tmpl
        print(f"✅ Шаблон кнопки загружен: {path}")
        return True

    def set_fallback_button(self, x, y):
        """
        Set fallback button coordinates for click if template not found.
        Coordinates in screen pixels (raw screenshot).
        """
        self.fallback_btn = (int(x), int(y))
        print(f"🧷 Fallback-кнопка установлена: {self.fallback_btn}")

    def _analyze_image_features(self, img):
        """Analyze image features to determine if it's likely an ad popup"""
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Look for UI elements typical of ad popups
        # 1. Brightness analysis (ad popups often have bright backgrounds)
        mean_brightness = np.mean(gray)
        
        # 2. Edge detection (UI elements have more structured edges)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
        
        # 3. Color distribution analysis (ad popups often have specific color patterns)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation_mean = np.mean(hsv[:,:,1])
        
        return {
            'brightness': mean_brightness,
            'edge_density': edge_density,
            'saturation': saturation_mean
        }

    def _adaptive_threshold_adjustment(self, success_history):
        """Adjust threshold based on recent success rate"""
        if not success_history:
            return self.button_threshold
            
        recent_successes = sum(1 for s in success_history[-10:] if s)
        recent_attempts = len(success_history[-10:])
        
        if recent_attempts == 0:
            return self.button_threshold
            
        success_rate = recent_successes / recent_attempts
        
        # Adjust threshold based on success rate
        if success_rate < 0.3:  # Too many failures, lower threshold
            self.adaptive_threshold = max(0.6, self.button_threshold - 0.1)
        elif success_rate > 0.8:  # Many successes, can be more strict
            self.adaptive_threshold = min(0.9, self.button_threshold + 0.05)
        else:  # Maintain current threshold
            self.adaptive_threshold = self.button_threshold
            
        return self.adaptive_threshold

    def detect_endgame_popup(self, img):
        """
        Return (is_popup, btn_x, btn_y) or (False, None, None).

        is_popup = True:
          – either template confidently found,
          – or fallback triggered (when we're sure it's end of game).
        """
        if img is None:
            return False, None, None

        if self.roi is None:
            self.set_roi(img.shape)  # default wide area

        x1, y1, x2, y2 = self.roi
        roi = img[y1:y2, x1:x2]

        # Analyze image features to determine if likely popup
        features = self._analyze_image_features(roi)
        
        # Adjust threshold based on learning
        current_threshold = self._adaptive_threshold_adjustment(self.attempt_history)
        
        # 1. If no template — immediately fallback if it's available and features suggest popup
        if self.button_template is None:
            if self.use_fallback_if_not_found and self.fallback_btn:
                # Only use fallback if features suggest it's likely a popup
                if features['brightness'] > 100:  # Bright UI is common in popups
                    fx, fy = self.fallback_btn
                    return True, fx, fy
            return False, None, None

        # 2. Search for button by template
        tmpl = self.button_template
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        tmpl_gray = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(roi_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= current_threshold:
            # Center of found button in ROI coordinates
            th, tw = tmpl_gray.shape[:2]
            bx = max_loc[0] + tw // 2
            by = max_loc[1] + th // 2

            # Convert to global screen coordinates
            btn_x = x1 + bx
            btn_y = y1 + by
            return True, btn_x, btn_y

        # 3. Template didn't reach threshold — use fallback if it exists
        if self.use_fallback_if_not_found and self.fallback_btn:
            fx, fy = self.fallback_btn
            return True, fx, fy

        # Nothing found
        return False, None, None

    def tap_ad_button(self, adb_cmd, bx=None, by=None, record_result=True):
        """
        Tap ad button:
          - if bx/by passed → tap there;
          - otherwise take fallback (constants / set_fallback_button).

        adb_cmd — function like screen_processor.adb_command.
        Return True/False based on actual success.
        """
        if adb_cmd is None:
            print("❌ adb_cmd не передан в tap_ad_button")
            if record_result:
                self.attempt_history.append(False)
            return False

        # button coordinates
        if bx is None or by is None:
            if self.fallback_btn:
                bx, by = self.fallback_btn
            else:
                bx, by = AD_BTN_X, AD_BTN_Y

        x = int(bx)
        y = int(by)

        res = send_tap_like_mouse(adb_cmd, x, y)
        if not res:
            print("❌ Команда tap не выполнилась")
            if record_result:
                self.attempt_history.append(False)
            return False

        print(f"✅ Нажал кнопку рекламы в точке ({bx}, {by})")
        if record_result:
            self.attempt_history.append(True)
        return True

    def record_ad_result(self, success: bool, context: dict = None):
        """Record the result of an ad interaction for learning purposes"""
        self.attempt_history.append(success)
        
        # Update learning engine with the result
        episode_data = {
            'success': success,
            'context': context or {},
            'timestamp': __import__('time').time()
        }
        
        # Create a simple "episode" for the learning engine
        from learning_engine import GameEpisode
        # This is a simplified representation for ad detection learning
        dummy_board = [[0 for _ in range(4)] for _ in range(4)]
        ad_episode = GameEpisode(
            board_states=[dummy_board],
            moves=[(0, 0)],
            scores=[1 if success else 0],
            final_score=1 if success else 0,
            max_tile=0,
            duration=0,
            timestamp=__import__('time').time(),
            success=success
        )
        
        self.learning_engine.record_episode(ad_episode)

    def get_detection_confidence(self) -> float:
        """Get confidence level based on recent success rate"""
        if not self.attempt_history:
            return 0.5  # Default confidence
            
        recent_successes = sum(1 for s in self.attempt_history[-10:] if s)
        recent_attempts = len(self.attempt_history[-10:])
        
        if recent_attempts == 0:
            return 0.5
            
        return recent_successes / recent_attempts

    def reset_learning(self):
        """Reset the learning state"""
        self.attempt_history = []
        self.success_rate = 0.0
        self.adaptive_threshold = self.button_threshold
        self.learning_engine.reset_learning()