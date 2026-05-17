import cv2

from app_paths import resource_path


class MouseCursor:
    def __init__(self):
        cursor_files = {
            'APPSTARTING': 'appstarting.png',
            'ARROW': 'arrow.png',
            'CROSS': 'cross.png',
            'HAND': 'hand.png',
            'HELP': 'help.png',
            'IBEAM': 'ibeam.png',
            'NO': 'no.png',
            'SIZENESW': 'sizenesw.png',
            'SIZENS': 'sizens.png',
            'SIZENWSE': 'sizenwse.png',
            'SIZEWE': 'sizewe.png',
            'UPARROW': 'uparrow.png',
            'WAIT': 'wait.png',
        }
        self.cursors = {
            name: cv2.imread(resource_path('cursors', file_name), cv2.IMREAD_UNCHANGED)
            for name, file_name in cursor_files.items()
        }

    def draw(self, image, x, y, cursor_type):
        if cursor_type not in self.cursors or self.cursors[cursor_type] is None:
            cursor_type = 'ARROW'

        cursor = self.cursors.get(cursor_type)
        if cursor is None:
            return image

        h, w = cursor.shape[:2]
        H, W = image.shape[:2]
        if h > H or w > W:
            return image

        x = max(0, min(x, W - w))
        y = max(0, min(y, H - h))

        alpha = cursor[:, :, 3] / 255.0

        for c in range(0, 3):
            image[y:y + h, x:x + w, c] = (
                alpha * cursor[:, :, c] +
                (1 - alpha) * image[y:y + h, x:x + w, c]
            )

        return image
