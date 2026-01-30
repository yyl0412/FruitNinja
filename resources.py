import os
import cv2
import numpy as np
import pygame
from config import WIDTH, HEIGHT, FRUIT_CONFIG


class ResourceManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.background = None
        pygame.mixer.init()
        self.load_assets()

    def load_assets(self):
        # --- 加载背景 ---
        bg_path = os.path.join('assets', 'background.jpg')
        if os.path.exists(bg_path):
            bg = cv2.imread(bg_path)
            self.background = cv2.resize(bg, (WIDTH, HEIGHT))
        else:
            print("提示: 未找到 assets/background.jpg，将使用黑色背景。")
            self.background = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        # --- 加载音效 ---
        try:
            slice_path = os.path.join('assets', 'slice.mp3')
            if os.path.exists(slice_path):
                self.sounds['slice'] = pygame.mixer.Sound(slice_path)
                self.sounds['slice'].set_volume(0.6)

            bomb_sound_path = os.path.join('assets', 'bomb.mp3')
            if os.path.exists(bomb_sound_path):
                self.sounds['bomb'] = pygame.mixer.Sound(bomb_sound_path)
                self.sounds['bomb'].set_volume(1.0)
        except Exception as e:
            print(f"警告: 音效加载失败 - {e}")

        # --- 加载图片 ---
        for name, config in FRUIT_CONFIG.items():
            base_path = os.path.join('assets', f'{name}.png')
            half1_path = os.path.join('assets', f'{name}_1.png')
            half2_path = os.path.join('assets', f'{name}_2.png')

            if os.path.exists(base_path):
                target_size = config['scale']
                self.images[name] = self._load_and_resize(base_path, target_size)

                # 加载切半图片，如果不存在则使用原图
                self.images[f'{name}_1'] = self._load_and_resize(half1_path, target_size) if os.path.exists(
                    half1_path) else self.images[name]
                self.images[f'{name}_2'] = self._load_and_resize(half2_path, target_size) if os.path.exists(
                    half2_path) else self.images[name]

        # 加载炸弹图片
        bomb_path = os.path.join('assets', 'bomb.png')
        if os.path.exists(bomb_path):
            self.images['bomb'] = self._load_and_resize(bomb_path, 80)

    def _load_and_resize(self, path, size):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None: return None
        h, w = img.shape[:2]
        scale = size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()
