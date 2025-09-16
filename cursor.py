import cv2


class MouseCursor:
    def __init__(self):
        # Загружаем изображения курсоров
        self.cursors = {
            'APPSTARTING': cv2.imread('cursors/appstarting.png', cv2.IMREAD_UNCHANGED),  # Курсор, который отображается при запуске приложения.
            'ARROW': cv2.imread('cursors/arrow.png', cv2.IMREAD_UNCHANGED),  # Стандартный курсор в виде стрелки.
            'CROSS': cv2.imread('cursors/cross.png', cv2.IMREAD_UNCHANGED),  # Курсор в виде перекрестия, обычно используется для выбора пикселей в графических редакторах.
            'HAND': cv2.imread('cursors/hand.png', cv2.IMREAD_UNCHANGED),  # Курсор в виде руки, обычно используется для ссылок в веб-браузерах.
            'HELP': cv2.imread('cursors/help.png', cv2.IMREAD_UNCHANGED),  # Курсор, который отображает значок помощи или вопросительный знак.
            'IBEAM': cv2.imread('cursors/ibeam.png', cv2.IMREAD_UNCHANGED),  # Курсор в виде вертикальной линии, который отображается при выборе текста.
            'NO': cv2.imread('cursors/no.png', cv2.IMREAD_UNCHANGED),  # Курсор, который отображает знак “запрещено” или “нет”.
            # 'SIZE': cv2.imread('./cursors/size.png', cv2.IMREAD_UNCHANGED),  Курсор для изменения размера объекта.
            #  'SIZEALL': cv2.imread('./cursors/sizeall.png', cv2.IMREAD_UNCHANGED),  Курсор для изменения размера объекта во всех направлениях.
            'SIZENESW': cv2.imread('cursors/sizenesw.png', cv2.IMREAD_UNCHANGED),  # Курсор для изменения размера объекта по диагонали (северо-восток/юго-запад).
            'SIZENS': cv2.imread('cursors/sizens.png', cv2.IMREAD_UNCHANGED),  # Курсор для изменения размера объекта вертикально (север/юг).
            'SIZENWSE': cv2.imread('cursors/sizenwse.png', cv2.IMREAD_UNCHANGED),  # Курсор для изменения размера объекта по диагонали (северо-запад/юго-восток).
            'SIZEWE': cv2.imread('cursors/sizewe.png', cv2.IMREAD_UNCHANGED),  # Курсор для изменения размера объекта горизонтально (запад/восток).
            'UPARROW': cv2.imread('cursors/uparrow.png', cv2.IMREAD_UNCHANGED),  # Курсор в виде стрелки, указывающей вверх.
            'WAIT': cv2.imread('cursors/wait.png', cv2.IMREAD_UNCHANGED)  # Курсор, который отображает значок ожидания или песочные часы.
        }

        # # Уменьшаем изображения стрелок
        # for key in self.cursors:
        #     self.cursors[key] = cv2.resize(self.cursors[key], (0, 0), fx=0.5, fy=0.5)

    def draw(self, image, x, y, cursor_type):
        # print("cursor_type - ", cursor_type)
        # Если тип курсора неизвестен, используем стрелку по умолчанию
        if cursor_type not in self.cursors:
            cursor_type = 'ARROW'

        # Выбираем изображение курсора
        cursor = self.cursors[cursor_type]

        # Рисуем курсор в позиции курсора мыши
        h, w = cursor.shape[:2]
        H, W = image.shape[:2]

        # Проверяем, что курсор не выходит за пределы изображения
        x = min(x, W - w)
        y = min(y, H - h)

        # Извлекаем альфа-канал из изображения курсора
        alpha = cursor[:, :, 3] / 255.0

        # Накладываем изображение курсора на изображение
        for c in range(0, 3):
            image[y:y + h, x:x + w, c] = (alpha * cursor[:, :, c] +
                                          (1 - alpha) * image[y:y + h, x:x + w, c])

        return image
