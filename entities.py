import random
import cv2
from config import WIDTH, HEIGHT, GRAVITY, FRUIT_CONFIG
from utils import overlay_transparent


class GameObject:
    """游戏对象类（水果/炸弹），处理位置、运动、绘制逻辑"""
    def __init__(self, is_half=False, base_obj=None, half_type=1, speed_bonus=0):
        # 如果是拆分后的半个水果，初始化半果属性
        if is_half and base_obj:
            self.init_as_half(base_obj, half_type)
        # 否则初始化完整的游戏对象（水果/炸弹）
        else:
            self.reset(speed_bonus)

    def reset(self, speed_bonus=0):
        """重置游戏对象属性（生成新的水果/炸弹）"""
        # 初始化水平位置（左右留100像素边界）
        self.x = random.randint(100, WIDTH - 100)
        self.y = HEIGHT  # 初始垂直位置在屏幕底部
        # 初始化垂直速度（向上运动，包含速度加成）
        base_speed_min = 18
        base_speed_max = 24
        self.speed_y = -random.randint(base_speed_min, base_speed_max) - speed_bonus
        # 初始化水平速度（随机左右方向，3-6像素/帧）
        self.speed_x = random.choice([-1, 1]) * random.randint(3, 6)
        self.gravity = GRAVITY  # 重力加速度（使物体下落）
        self.angle = 0  # 初始旋转角度
        self.spin_speed = random.choice([-8, 8, -5, 5])  # 旋转速度（随机方向和速率）
        self.active = True  # 对象是否活跃（未落地/未被消除）
        self.is_bomb = False  # 是否是炸弹

        # 15%概率生成炸弹
        if random.random() < 0.15:
            self.is_bomb = True
            self.name = 'bomb'
            self.radius = 40  # 炸弹碰撞半径
        else:
            # 随机选择水果类型，读取配置中的碰撞半径
            self.name = random.choice(list(FRUIT_CONFIG.keys()))
            self.radius = FRUIT_CONFIG[self.name]['scale'] // 2 + 10

    def init_as_half(self, parent, half_type):
        """初始化拆分后的半个水果属性"""
        self.name = f"{parent.name}_{half_type}"  # 半果命名（区分左右/上下）
        self.x = parent.x  # 继承原水果的位置
        self.y = parent.y
        self.angle = parent.angle  # 继承原水果的旋转角度
        self.gravity = GRAVITY + 0.1  # 半果重力稍大，下落更快
        self.is_bomb = False  # 炸弹不拆分
        self.active = True
        self.radius = 0  # 半果暂不设置碰撞半径

        # 半果分离速度（1型向右，2型向左）
        diverge_speed = 6 if half_type == 1 else -6
        self.speed_x = parent.speed_x + diverge_speed  # 继承原速度+分离速度
        self.speed_y = random.uniform(2, 5)  # 半果初始向下速度
        self.spin_speed = parent.spin_speed * 1.5  # 半果旋转速度更快

    def move(self):
        """更新对象的位置和旋转角度（每一帧调用）"""
        self.x += self.speed_x  # 更新水平位置
        self.y += self.speed_y  # 更新垂直位置
        self.speed_y += self.gravity  # 重力影响垂直速度（加速下落）
        self.angle += self.spin_speed  # 更新旋转角度

        # 超出屏幕底部100像素后，标记为非活跃
        if self.y > HEIGHT + 100:
            self.active = False

    def draw(self, img, resource_manager):
        """绘制游戏对象到图像上"""
        if not self.active: return  # 非活跃对象不绘制

        # 优先使用资源管理器中的图像绘制（带透明和旋转）
        if self.name in resource_manager.images and resource_manager.images[self.name] is not None:
            overlay_transparent(img, resource_manager.images[self.name], self.x, self.y, self.angle)
        else:
            # 图像资源缺失时的降级绘制逻辑
            if self.is_bomb:
                # 绘制黑色圆形炸弹 + 红色感叹号
                cv2.circle(img, (int(self.x), int(self.y)), 40, (30, 30, 30), -1)
                cv2.putText(img, "!", (int(self.x) - 10, int(self.y) + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                # 绘制水果颜色的圆形占位符
                color = FRUIT_CONFIG.get(self.name, {}).get('color', (255, 255, 255))
                cv2.circle(img, (int(self.x), int(self.y)), 40, color, -1)


class Particle:
    """粒子效果类（用于水果消除等视觉反馈）"""
    def __init__(self, x, y, color):
        self.x, self.y = x, y  # 粒子初始位置
        self.color = color  # 粒子颜色
        self.vx = random.uniform(-10, 10)  # 水平速度（随机）
        self.vy = random.uniform(-10, 10)  # 垂直速度（随机）
        self.size = random.randint(4, 10)  # 粒子初始尺寸
        self.life = 10  # 粒子生命周期（帧数）

    def update(self):
        """更新粒子位置和生命周期（每一帧调用）"""
        self.x += self.vx
        self.y += self.vy
        self.life -= 1  # 生命周期递减
        self.size = max(0, self.size - 0.5)  # 粒子逐渐缩小（最小为0）

    def draw(self, img):
        """绘制粒子（矩形）"""
        if self.life > 0:  # 生命周期>0时才绘制
            p1 = (int(self.x - self.size), int(self.y - self.size))
            p2 = (int(self.x + self.size), int(self.y + self.size))
            cv2.rectangle(img, p1, p2, self.color, -1)  # 填充矩形绘制粒子