from win32con import IDC_APPSTARTING, IDC_ARROW, IDC_CROSS, IDC_HAND, IDC_HELP, IDC_SIZEALL, IDC_UPARROW, IDC_WAIT, \
    IDC_SIZEWE, IDC_SIZENWSE, IDC_SIZENS, IDC_SIZENESW, IDC_SIZE, IDC_NO, IDC_ICON, IDC_IBEAM
from win32gui import LoadCursor, GetCursorInfo

DEFAULT_CURSORS = {
    LoadCursor(0, IDC_APPSTARTING): 'APPSTARTING',
    LoadCursor(0, IDC_ARROW): 'ARROW',
    LoadCursor(0, IDC_CROSS): 'CROSS',
    LoadCursor(0, IDC_HAND): 'HAND',
    LoadCursor(0, IDC_HELP): 'HELP',
    LoadCursor(0, IDC_IBEAM): 'IBEAM',
    LoadCursor(0, IDC_ICON): 'ICON',
    LoadCursor(0, IDC_NO): 'NO',
    LoadCursor(0, IDC_SIZE): 'SIZE',
    LoadCursor(0, IDC_SIZEALL): 'SIZEALL',
    LoadCursor(0, IDC_SIZENESW): 'SIZENESW',
    LoadCursor(0, IDC_SIZENS): 'SIZENS',
    LoadCursor(0, IDC_SIZENWSE): 'SIZENWSE',
    LoadCursor(0, IDC_SIZEWE): 'SIZEWE',
    LoadCursor(0, IDC_UPARROW): 'UPARROW',
    LoadCursor(0, IDC_WAIT): 'WAIT'
}


def get_current_cursor():
    curr_cursor_handle = GetCursorInfo()[1]
    return DEFAULT_CURSORS.get(curr_cursor_handle)
