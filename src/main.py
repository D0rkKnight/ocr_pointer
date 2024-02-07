from PyQt5.QtGui import QKeyEvent
import pytesseract
from PIL import Image, ImageDraw
import pyautogui
from PyQt5 import QtWidgets, QtCore, QtGui
import argparse
import keyboard
from pydantic import BaseModel
from PyQt5.QtCore import QTimer

import math
import threading

# Path to tesseract executable - adjust it according to your installation
pytesseract.pytesseract.tesseract_cmd = r'D:\Programs\Tesseract\tesseract.exe'  # Windows example
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Linux example
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'  # macOS example

class WordBox(BaseModel):
    box: tuple
    word: str

def capture_screen():
    """Capture the screen and return it as a PIL image."""
    return pyautogui.screenshot()

def find_all_words(image):
    """Use OCR to find all words in the 'image'."""
    # Convert image to RGB (if not already in that format)
    rgb_im = image.convert('RGB')
    
    # Perform OCR
    data = pytesseract.image_to_data(rgb_im, output_type=pytesseract.Output.DICT)
    word_boxes = []
    for i, text in enumerate(data['text']):
        if text:
            # Scale the coordinates
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            word_boxes.append(WordBox(box=(x, y, w, h), word=text))
    return word_boxes

class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, boxes):
        super().__init__()
        self.boxes = boxes
        self.selected_box = 0  # Index of the currently selected box
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.showFullScreen()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        for i, box in enumerate(self.boxes):
            if i == self.selected_box:
                painter.setPen(QtGui.QPen(QtGui.QColor('yellow'), 2))  # Yellow for the selected box
            else:
                painter.setPen(QtGui.QPen(QtGui.QColor('red'), 2))  # Red for the other boxes
            painter.drawRect(QtCore.QRect(*box.box))

    def keyPressEvent(self, event):
        
        if event.key() == QtCore.Qt.Key_Tab:
            self.tabBox()
        elif event.key() == QtCore.Qt.Key_Return:
            self.enterBox()
        else:
            # Close the application when any other key is pressed
            self.disappear()
    
    def tabBox(self):
        self.selected_box = (self.selected_box + 1) % len(self.boxes)
        self.update()
    
    def enterBox(self):
        box = self.boxes[self.selected_box].box
        x, y, w, h = box
        pyautogui.click(x + w / 2, y + h / 2)
        self.disappear()
    
    def recalcSelectedBox(self):
        # Make sure that the selected box is within the valid range
        self.selected_box = max(0, min(self.selected_box, len(self.boxes) - 1))
    
    def disappear(self):
        # self.setWindowState(QtCore.Qt.WindowMinimized)
        self.close()
    
    

class MyLineEdit(QtWidgets.QLineEdit):
    def __init__(self, overlay, app, *args, **kwargs):
        super(MyLineEdit, self).__init__(*args, **kwargs)
        self.overlay = overlay
        self.app = app

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Tab:
            # Select the next box
            self.overlay.tabBox()
        elif event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            # Filter the boxes based on the entered word
            
            # Cloes this text field
            self.destroy()
            
            self.overlay.enterBox()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.destroy()
            self.overlay.disappear()

        else:
            super(MyLineEdit, self).keyPressEvent(event)



def update_overlay(overlay, word, all_boxes):
    
    print(f"Searching for '{word}'")
    print(f"Current thread is {threading.current_thread()}")
    
    # Filter the boxes based on the entered word
    overlay.boxes = [box for box in all_boxes if word.lower() in box.word.lower()]
    overlay.recalcSelectedBox()
    overlay.update()  # Redraw the boxes

all_boxes = []
box_timer = None
def search(app, overlay):
    global all_boxes, box_timer
    
    screen = capture_screen()
    overlay.show()
    
    # Create a text field to enter the word to find
    text_field = MyLineEdit(overlay, app)
    text_field.show()
    
    # Bring the window to the front
    text_field.activateWindow()
    text_field.raise_()
    
    def find_words_and_update_overlay(overlay, screen):
        global all_boxes, box_timer
        all_boxes = find_all_words(screen)
        overlay.boxes = all_boxes
        
        update_overlay(overlay, text_field.text(), all_boxes)
        return all_boxes

    # Create a new thread that will run the find_words_and_update_overlay function
    thread = threading.Thread(target=find_words_and_update_overlay, args=(overlay, screen))

    # Start the new thread
    thread.start()
    
    def check_thread_done():
        global all_boxes
        
        if not thread.is_alive():
            # The thread has finished
            box_timer.stop()
            text_field.textChanged.connect(lambda: update_overlay(overlay, text_field.text(), all_boxes))
    
    box_timer = QtCore.QTimer()
    box_timer.timeout.connect(check_thread_done)
    box_timer.start(16)  # 60 FPS (1000 ms / 60 = 16.6667 ms)

search_requested = False

def main():
    global search_requested
    
    app = QtWidgets.QApplication([])

    overlay = OverlayWindow([])
    
    def request_search():
        global search_requested
        search_requested = True
    
    def check_search_request():
        global search_requested
        if search_requested:
            search(app, overlay)
            search_requested = False
        
    timer = QtCore.QTimer()
    timer.timeout.connect(check_search_request)
    timer.start(16)  # 60 FPS (1000 ms / 60 = 16.6667 ms)
        
    keyboard.add_hotkey('ctrl+shift+alt+s', request_search)
    
    
    search(app, overlay)

    # Step 4: Start the application
    app.exec_()
    

# Example usage
if __name__ == "__main__":
    main()
