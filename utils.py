import cv2
import numpy as np


def overlay_transparent(background, overlay, x, y, angle=0):
    """
    在背景图像上叠加带透明通道的图像（支持旋转）
    :param background: 背景图像（numpy数组）
    :param overlay: 叠加图像（带alpha通道的4通道图像）
    :param x: 叠加图像中心的x坐标
    :param y: 叠加图像中心的y坐标
    :param angle: 旋转角度（默认0，不旋转）
    :return: 叠加后的背景图像
    """
    # 获取背景和叠加图像的高、宽
    h_bg, w_bg = background.shape[:2]
    h_fg, w_fg = overlay.shape[:2]

    # 如果需要旋转，先对叠加图像进行旋转变换
    if angle != 0:
        # 计算旋转矩阵（以图像中心为旋转点，旋转angle度，缩放比例1.0）
        M = cv2.getRotationMatrix2D((w_fg // 2, h_fg // 2), angle, 1.0)
        # 提取旋转矩阵中的余弦和正弦值，用于计算旋转后的图像尺寸
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        # 计算旋转后图像的新宽高（避免旋转后图像被裁剪）
        new_w = int((h_fg * sin) + (w_fg * cos))
        new_h = int((h_fg * cos) + (w_fg * sin))
        # 调整旋转矩阵，使旋转后的图像居中
        M[0, 2] += (new_w / 2) - w_fg / 2
        M[1, 2] += (new_h / 2) - h_fg / 2
        # 执行旋转变换
        overlay = cv2.warpAffine(overlay, M, (new_w, new_h))
        # 更新旋转后叠加图像的宽高
        h_fg, w_fg = overlay.shape[:2]

    # 计算叠加图像在背景上的左上角坐标（以传入的x,y为中心）
    x = int(x - w_fg / 2)
    y = int(y - h_fg / 2)

    # 检查叠加图像是否超出背景范围，超出则直接返回原背景
    if x < 0 or y < 0 or x + w_fg > w_bg or y + h_fg > h_bg:
        return background

    # 提取背景中对应叠加区域的ROI
    roi = background[y:y + h_fg, x:x + w_fg]

    # 处理带alpha通道的叠加逻辑
    if overlay.shape[2] == 4:
        # 提取alpha通道并归一化到0-1范围（用于透明度混合）
        alpha = overlay[:, :, 3] / 255.0
        # 提取叠加图像的RGB通道
        overlay_rgb = overlay[:, :, :3]
        # 计算反向alpha（背景的权重）
        alpha_inv = 1.0 - alpha
        # 按通道进行透明度混合：前景*alpha + 背景*alpha_inv
        for c in range(3):
            roi[:, :, c] = (alpha * overlay_rgb[:, :, c] + alpha_inv * roi[:, :, c])
    else:
        # 无alpha通道时直接覆盖
        roi[:] = overlay

    # 将混合后的ROI放回背景图像
    background[y:y + h_fg, x:x + w_fg] = roi
    return background
