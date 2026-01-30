import cv2
from config import WIDTH, HEIGHT, PALETTE, FRUIT_CONFIG
from utils import overlay_transparent


def draw_tutorial(frame, resource_manager):
    """绘制半透明的新手教程层"""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (WIDTH, HEIGHT), PALETTE['tutorial_bg'], -1)
    frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

    # 文本说明
    cv2.putText(frame, "HOW TO PLAY", (50, 80), cv2.FONT_HERSHEY_TRIPLEX, 2, PALETTE['highlight'], 3)
    cv2.putText(frame, "1. Use your INDEX FINGER as a blade.", (60, 150), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255),
                1)
    cv2.putText(frame, "2. Slice fruits to get score.", (60, 190), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 1)
    cv2.putText(frame, "3. AVOID BOMBS! They reduce 1 LIFE.", (60, 240), cv2.FONT_HERSHEY_DUPLEX, 1.0, (50, 50, 255), 2)
    cv2.putText(frame, "SCORES:", (60, 320), cv2.FONT_HERSHEY_TRIPLEX, 1.2, PALETTE['highlight'], 2)

    start_y = 380
    start_x = 80
    gap_x = 220

    # 绘制水果图示
    fruit_items = list(FRUIT_CONFIG.items())
    for i, (name, config) in enumerate(fruit_items):
        row = i // 3
        col = i % 3
        pos_x = start_x + col * gap_x
        pos_y = start_y + row * 100

        if name in resource_manager.images and resource_manager.images[name] is not None:
            icon = cv2.resize(resource_manager.images[name], (50, 50))
            overlay_transparent(frame, icon, pos_x, pos_y - 15)
        else:
            cv2.circle(frame, (pos_x, pos_y - 15), 20, config['color'], -1)

        label = f"{config.get('label', name).upper()}"
        score_text = f"+{config['score']} Pts"

        cv2.putText(frame, label, (pos_x + 40, pos_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, score_text, (pos_x + 40, pos_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.rectangle(frame, (WIDTH // 2 - 200, HEIGHT - 150), (WIDTH // 2 + 200, HEIGHT - 80), (0, 100, 0), 2)
    cv2.putText(frame, "Press 'S' to START", (WIDTH // 2 - 160, HEIGHT - 105), cv2.FONT_HERSHEY_DUPLEX, 1.2,
                (0, 255, 0), 2)

    return frame
