#!/usr/bin/python3
# -*- coding: utf-8 -*-

import yaml
import sys
import signal
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *

app = QApplication(sys.argv)

def sigint_handler(*args):
    app.quit()

signal.signal(signal.SIGINT, sigint_handler)

imagecache = {}

frameNr = 0

def fileChanged(name):
  print("Detected changed file", name)
  if name != "jimi.yaml":
    if name in imagecache:
      del imagecache[name]
    else:
      print(name, "was not loaded!")
  loadFrameData()
  advanceFrame()

watcher = QFileSystemWatcher()
watcher.fileChanged.connect(fileChanged)

class Frame:
  x = None
  y = None
  scale = None
  name = None
  filename = None
  data = None
  path = None

  def __init__(self, name, filename, x, y, scale, invert):
    self.x = x
    self.y = y
    self.scale = scale
    self.name = name
    self.filename = filename
    path = "/home/dos/Dokumenty/jimi/"+filename
    if path not in imagecache:
      print("Loading", filename)
      imagecache[path] = QImage(path)
      if invert:
        imagecache[path].invertPixels()
      watcher.addPath(path)
      if imagecache[path].isNull():
        print('WARNING: Could not load', filename)
    self.path = path
    self.data = imagecache[path]

  def __repr__(self):
    return self.name + ":" + self.filename

  def getImage(self):
    return self.data

  def getFilename(self):
    return self.filename

  def getPath(self):
    return self.path

  def getSize(self):
    return self.data.size()

  def getX(self):
    return self.x

  def getY(self):
    return self.y

  def getScale(self):
    return self.scale

  def isCorrect(self):
    return self.data and not self.data.isNull()


def fillDefaults(data):
  if not 'name' in data:
      print('ERROR: approached a segment without name', data)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Approached a segment without name!').exec_()
      return False
  if not 'framelen' in data:
      print('ERROR: approached a segment without framelen', data)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Approached a segment without framelen!').exec_()
      return False
  if not 'from' in data:
      print('ERROR: approached a segment without from field', data)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Approached a segment without from field!').exec_()
      return False
  if not 'len' in data and not 'to' in data:
      print('ERROR: approached a segment without len nor to field', data)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Approached a segment without len nor to field!').exec_()
      return False
  if not 'filename' in data:
      data['filename'] = data['name']
  if not 'to' in data:
      data['to'] = data['from'] + data['len']
  if not 'len' in data:
      data['len'] = data['to'] - data['from'] + 1
  if not 'after' in data:
      data['after'] = None
  if not 'frameoffset' in data:
      data['frameoffset'] = 0
  if not 'offset' in data:
      data['offset'] = 0
  if not 'startoffset' in data:
      data['startoffset'] = 0
  if not 'endoffset' in data:
      data['endoffset'] = 0
  if not 'loop' in data:
      data['loop'] = True
  if not 'x' in data:
      data['x'] = 0
  if not 'y' in data:
      data['y'] = 0
  if not 'scale' in data:
      data['scale'] = 1
  if not 'invert' in data:
      data['invert'] = True
  return True

seqends = None
frames = None

def loadFrameData():

  global seqends, frames

  print("Loading frame data...")

  with open("jimi.yaml") as f:
    data = yaml.load(f)
  watcher.addPath("jimi.yaml")

  seqends = {}

  lastname = ""
  frames = []
  
  errorhappened = False

  for i in range(0, 5936):
    frames.append([])
  
  for frameset in data:
    if not fillDefaults(frameset):
      errorhappened = True
      continue
    name = frameset["name"]
    if name in seqends:
      print('ERROR: segment', name, 'already exists!', frameset)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Segment '+ name + ' already exists!').exec_()
      errorhappened = True
      continue
    filename = name
    if frameset["filename"]:
      filename = frameset["filename"]
    starttime = 0
    if frameset["after"]:
      if frameset["after"] in seqends:
        starttime = seqends[frameset["after"]]
      else:
        print('WARNING: segment', name, 'specified non-existent segment', frameset["after"], 'as its "after" field!')
        QMessageBox(QMessageBox.Warning, 'Incorrect after field', 'Segment' + name + 'specified non-existent segment' + str(frameset["after"]) + 'as its "after" field!').exec_()
        errorhappened = True
    elif lastname:
      starttime = seqends[lastname]
    length = frameset["len"]
    if not length:
      length = frameset["to"] - frameset["from"]
  
    endtime = starttime + length * frameset["framelen"] + frameset["endoffset"] + frameset["offset"]
    starttime += frameset["startoffset"] + frameset["offset"]

    frame = frameset["from"]
    offset = frameset["frameoffset"]
    counter = offset
    if counter < 0 and frameset["loop"]:
      frame = frameset["to"] - ((-offset) // frameset["framelen"])
      counter = frameset["framelen"] - (-offset) % frameset["framelen"]
    for i in range(starttime, endtime):
      if counter >= frameset["framelen"]:
        counter=0
        frame+=1
        if frame > frameset["to"]:
          if frameset["loop"]:
            frame = frameset["from"]
          else:
            frame = frameset["to"]
      counter+=1
      img = Frame(name, filename + str(frame).zfill(2) + ".png", frameset["x"], frameset["y"], frameset["scale"], frameset["invert"])
      frames[i].append(img)
      if not img.isCorrect():
        path = img.getPath()
        if path in imagecache:
          del imagecache[path]
        errorhappened = True
  
    seqends[name] = endtime
    lastname = name
    
  palette = QPalette()
  palette.setColor(QPalette.WindowText, QColor('black'))
  if errorhappened:
    print('WARNING: Some files/segments could not be loaded!')
    palette.setColor(QPalette.WindowText, QColor('red'))
  label.setPalette(palette)
    
  slider.setMaximum(max(seqends.values()) * 1000/25 + 1000)
  print("Frame data loaded!")

def drawFrame(frame):
  painter.fillRect( QRectF(0, 0, 1280, 720), QColor('black'))
  for img in frames[frame]:
    painter.drawImage(QRect(QPoint(img.getX(), img.getY()), img.getSize()*img.getScale()), img.getImage())
  scene.clear()
  scene.addPixmap(pixmap)
  view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
  label.setText('Frame ' + str(frame) + ' / ' + str(frames[frame]))

def advanceFrame():
    #global frameNr
    #frameNr += 1
    #print(frameNr)
    #drawFrame(frameNr)
    drawFrame(int(player.position() / 1000 / (1/25)))

def playPause():
    if player.state() == QMediaPlayer.PlayingState:
        player.pause()
        timer.stop()
        button.setText("Play")
    else:
        player.play()
        timer.start(1000/60)
        button.setText("Pause")

def positionChanged():
    if not slider.isSliderDown():
        slider.setSliderPosition(player.position())

def sliderReleased():
    if player.position() != slider.sliderPosition() and slider.sliderPosition() != slider.maximum():
        player.setPosition(slider.sliderPosition())
    advanceFrame()


w = QMainWindow()
w.resize(1303, 854)
w.setWindowTitle('Jimi.pl Editor')

view = QGraphicsView()
button = QPushButton("Play")
button.clicked.connect(playPause)

slider = QSlider()
slider.setOrientation(Qt.Horizontal)
slider.valueChanged.connect(sliderReleased)
slider.setSingleStep(1000/25)

pixmap	= QPixmap (QSize(1280,720))    
painter	= QPainter (pixmap)    
    
painter.fillRect( QRectF(0, 0, 1280, 720), QColor('black'))

timer = QTimer()
timer.timeout.connect(advanceFrame)

scene = QGraphicsScene()
scene.addPixmap(pixmap)
scene.setSceneRect(QRectF(pixmap.rect()))

view.setScene(scene)

label = QLabel()

vbox = QVBoxLayout()
vbox.addWidget(view)
vbox.addWidget(label)
vbox.addWidget(slider)
vbox.addWidget(button)
        
widget = QWidget()
widget.setLayout(vbox)    

url = QUrl.fromLocalFile("/home/dos/wieko/wieko_konkurs_jimipl.wav")
content = QMediaContent(url)
player = QMediaPlayer()
player.setMedia(content)
player.positionChanged.connect(positionChanged)

w.setCentralWidget(widget)

loadFrameData()
advanceFrame()
QTimer.singleShot(0, advanceFrame)

w.show()

sys.exit(app.exec_())
