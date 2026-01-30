import cv2
import mediapipe as mp
import numpy as np
import pygame
import random
import math
import time

# 导入自定义模块（游戏配置、资源管理、游戏实体、UI绘制）
from config import WIDTH, HEIGHT, PALETTE, FRUIT_CONFIG
from resources import ResourceManager
from entities import GameObject, Particle
from ui import draw_tutorial


def main():
    # 初始化资源管理器（加载图片、音效等资源）
    R = ResourceManager()

    # 初始化MediaPipe手部追踪和OpenCV摄像头
    mp_hands = mp.solutions.hands
    # 配置手部追踪：最多检测1只手，检测置信度阈值0.7
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

    # 打开摄像头并设置分辨率
    cap = cv2.VideoCapture(0)
    cap.set(3, WIDTH)
    cap.set(4, HEIGHT)

    # 游戏状态定义: 0=菜单, 1=游戏中, 2=游戏结束, 3=倒计时, 4=暂停
    game_state = 0

    # 游戏对象列表管理
    objects = []          # 活跃的水果/炸弹对象
    debris = []           # 被切开的半果碎片
    particles = []        # 切割特效粒子
    trail = []            # 手指追踪轨迹（刀光）

    # 游戏核心数据
    score = 0             # 得分
    lives = 3             # 生命值（切到炸弹扣血）
    frame_count = 0       # 帧数计数器（用于动态难度）
    countdown_timer = 0   # 倒计时帧数

    # --- 连击系统变量 ---
    combo_count = 0               # 连击数
    last_slice_time = 0           # 上一次切割时间
    combo_display_timer = 0       # 连击文字显示时长
    COMBO_TIMEOUT = 2.5           # 连击超时时间（秒）

    print("系统启动。\n请按 'S' 开始游戏。")

    while True:
        # 读取摄像头帧
        success, frame = cap.read()
        if not success: break  # 摄像头读取失败则退出循环

        # 水平翻转帧（镜像效果，操作更直观）
        frame = cv2.flip(frame, 1)
        # 转换颜色空间（MediaPipe需要RGB格式）
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ==================== 1. 核心画面构建 ====================
        # 优先使用自定义背景图，无则使用摄像头画面
        if R.background is not None:
            display_frame = R.background.copy()
        else:
            display_frame = frame

        # ==================== 2. 手部追踪 ====================
        results = hands.process(rgb_frame)
        tip = None  # 食指指尖坐标
        if results.multi_hand_landmarks:
            for hand_lm in results.multi_hand_landmarks:
                h, w, _ = frame.shape
                # 获取食指指尖（第8个关键点）的像素坐标
                tip = (int(hand_lm.landmark[8].x * w), int(hand_lm.landmark[8].y * h))
                trail.append(tip)  # 加入轨迹列表

        # 限制轨迹长度（最多10个点，避免轨迹过长）
        if len(trail) > 10: trail.pop(0)

        # 绘制刀光（轨迹线条，越新的点越粗）
        for i in range(1, len(trail)):
            thickness = int(np.sqrt(10 / float(i + 1)) * 10)
            cv2.line(display_frame, trail[i - 1], trail[i], (255, 255, 255), thickness)

        # ==================== 3. 游戏逻辑 ====================
        key = cv2.waitKey(1) & 0xFF  # 获取键盘输入

        if game_state == 0:
            # 菜单界面：绘制教程指引
            display_frame = draw_tutorial(display_frame, R)
            # 按S/空格开始游戏，进入倒计时状态
            if key == ord('s') or key == ord('S') or key == 32:
                game_state = 3
                countdown_timer = 90  # 3秒倒计时（按30FPS计算）
                frame_count = 0
                combo_count = 0
                print("游戏开始！")

        elif game_state == 1:
            # 游戏中状态
            frame_count += 1

            # 动态难度调节：每300帧提升一级难度
            difficulty_level = frame_count // 300
            # 难度越高，生成频率越快（最低10帧生成一次）
            spawn_rate = max(10, 35 - difficulty_level * 2)
            # 难度越高，水果速度越快（最高额外+5）
            speed_bonus = min(5, difficulty_level * 0.5)

            # 按生成频率生成水果/炸弹
            if frame_count % spawn_rate == 0:
                objects.append(GameObject(speed_bonus=speed_bonus))
                # 难度越高，有概率一次生成两个水果（最高60%概率）
                if random.random() < min(0.6, difficulty_level * 0.05):
                    objects.append(GameObject(speed_bonus=speed_bonus))

            # --- 处理游戏对象（水果/炸弹） ---
            for obj in objects[:]:  # 遍历副本避免删除元素导致的异常
                obj.move()  # 更新对象位置和旋转
                obj.draw(display_frame, R)  # 绘制对象

                # 检测手指是否切割到活跃的对象
                if tip and obj.active:
                    # 计算指尖到对象中心的距离
                    dist = math.hypot(tip[0] - obj.x, tip[1] - obj.y)
                    if dist < obj.radius:  # 距离小于碰撞半径=切割成功
                        obj.active = False  # 标记为非活跃

                        if obj.is_bomb:
                            # 切到炸弹：扣生命值、重置连击、播放音效、红色闪屏
                            lives -= 1
                            combo_count = 0
                            R.play_sound('bomb')
                            overlay = np.full_like(display_frame, (0, 0, 255))
                            display_frame = cv2.addWeighted(display_frame, 0.7, overlay, 0.3, 0)
                        else:
                            # 切到水果：处理连击逻辑
                            current_time = time.time()
                            if current_time - last_slice_time < COMBO_TIMEOUT:
                                combo_count += 1  # 在超时内切割，连击数+1
                            else:
                                combo_count = 1   # 超时重置为1连击

                            last_slice_time = current_time
                            combo_display_timer = 30  # 显示连击文字30帧

                            # 计算得分：基础分 + 连击加成
                            base_score = FRUIT_CONFIG[obj.name]['score']
                            score += base_score + (combo_count - 1)

                            R.play_sound('slice')  # 播放切割音效

                            # 生成两个半果碎片
                            debris.append(GameObject(is_half=True, base_obj=obj, half_type=1))
                            debris.append(GameObject(is_half=True, base_obj=obj, half_type=2))

                            # 生成10个粒子特效
                            p_color = FRUIT_CONFIG[obj.name]['color']
                            for _ in range(10):
                                particles.append(Particle(obj.x, obj.y, p_color))

                # 移除非活跃对象
                if not obj.active:
                    objects.remove(obj)

            # --- 处理碎片与粒子 ---
            # 更新并绘制半果碎片，移除非活跃碎片
            for d in debris[:]:
                d.move()
                d.draw(display_frame, R)
                if not d.active:
                    debris.remove(d)

            # 更新并绘制粒子，移除生命周期结束的粒子
            for p in particles[:]:
                p.update()
                p.draw(display_frame)
                if p.life <= 0:
                    particles.remove(p)

            # --- HUD显示（得分、生命值） ---
            # 绘制得分
            cv2.putText(display_frame, f"Score: {score}", (30, 60), cv2.FONT_HERSHEY_DUPLEX, 1.5, PALETTE['text'], 2)
            # 绘制生命值
            for i in range(lives):
                cv2.circle(display_frame, (WIDTH - 50 - i * 60, 50), 20, (50, 50, 220), -1)

            # --- 连击特效 ---
            if combo_count > 1 and combo_display_timer > 0:
                combo_text = f"{combo_count} COMBO!"
                # 连击数越多，文字越大（最大3.5倍）
                font_scale = min(3.5, 1.5 + combo_count * 0.2)
                text_size = cv2.getTextSize(combo_text, cv2.FONT_HERSHEY_TRIPLEX, font_scale, 3)[0]
                # 文字居中显示
                text_x = (WIDTH - text_size[0]) // 2
                text_y = HEIGHT // 2

                # 绘制文字阴影（黑色）+ 主体（配色表中的连击色）
                cv2.putText(display_frame, combo_text, (text_x + 5, text_y + 5), cv2.FONT_HERSHEY_TRIPLEX, font_scale,
                            (0, 0, 0), 3)
                cv2.putText(display_frame, combo_text, (text_x, text_y), cv2.FONT_HERSHEY_TRIPLEX, font_scale,
                            PALETTE['combo_text'], 3)
                combo_display_timer -= 1

            # 生命值<=0，进入游戏结束状态
            if lives <= 0:
                game_state = 2

            # 按P键暂停游戏
            if key == ord('p') or key == ord('P'):
                game_state = 4

        elif game_state == 2:
            # 游戏结束界面
            # 绘制半透明黑色覆盖层
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (0, 0, 0), -1)
            display_frame = cv2.addWeighted(overlay, 0.85, display_frame, 0.15, 0)

            # 计算文字居中坐标
            center_x, center_y = WIDTH // 2, HEIGHT // 2

            # 绘制游戏结束文字
            cv2.putText(display_frame, "GAME OVER", (center_x - 250, center_y - 80), cv2.FONT_HERSHEY_TRIPLEX, 3,
                        (0, 0, 255), 5)
            cv2.putText(display_frame, f"Final Score: {score}", (center_x - 150, center_y + 20),
                        cv2.FONT_HERSHEY_DUPLEX, 1.5, (255, 255, 255), 2)
            # 绘制重启/退出提示
            cv2.putText(display_frame, "[R] Restart", (center_x - 120, center_y + 120), cv2.FONT_HERSHEY_DUPLEX, 1,
                        (0, 255, 0), 2)
            cv2.putText(display_frame, "[Q] Quit", (center_x - 120, center_y + 170), cv2.FONT_HERSHEY_DUPLEX, 1,
                        (0, 100, 255), 2)

            # 按R重启游戏
            if key == ord('r') or key == ord('R'):
                score = 0
                lives = 3
                objects.clear()
                debris.clear()
                particles.clear()
                frame_count = 0
                combo_count = 0
                game_state = 1
            # 按Q退出游戏
            elif key == ord('q') or key == ord('Q'):
                break

        elif game_state == 3:
            # 3秒倒计时界面
            countdown_timer -= 1
            # 计算剩余秒数（向上取整）
            remaining_seconds = max(0, (countdown_timer + 29) // 30)

            # 绘制半透明黑色覆盖层
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (0, 0, 0), -1)
            display_frame = cv2.addWeighted(overlay, 0.7, display_frame, 0.3, 0)

            # 显示倒计时数字和准备提示
            if remaining_seconds > 0:
                cv2.putText(display_frame, str(remaining_seconds),
                            (WIDTH // 2 - 50, HEIGHT // 2 + 80),
                            cv2.FONT_HERSHEY_TRIPLEX, 5, (0, 255, 0), 8)
                cv2.putText(display_frame, "GET READY!",
                            (WIDTH // 2 - 150, HEIGHT // 2 - 50),
                            cv2.FONT_HERSHEY_DUPLEX, 2, (0, 255, 255), 3)
            else:
                game_state = 1  # 倒计时结束，进入游戏中状态

        elif game_state == 4:
            # 暂停界面
            # 绘制半透明黑色覆盖层
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), (0, 0, 0), -1)
            display_frame = cv2.addWeighted(overlay, 0.7, display_frame, 0.3, 0)

            # 绘制暂停文字和恢复提示
            cv2.putText(display_frame, "PAUSED",
                        (WIDTH // 2 - 120, HEIGHT // 2 - 30),
                        cv2.FONT_HERSHEY_TRIPLEX, 2.5, (0, 255, 255), 4)
            cv2.putText(display_frame, "Press 'P' to Resume",
                        (WIDTH // 2 - 120, HEIGHT // 2 + 50),
                        cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)

            # 按P恢复游戏
            if key == ord('p') or key == ord('P'):
                game_state = 1  # 恢复游戏

        # 按Q键强制退出
        if key == ord('q'):
            break

        # 显示游戏画面
        cv2.imshow('Fruit Ninja', display_frame)

    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()


if __name__ == "__main__":
    main()