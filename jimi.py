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

animWidth = 0
animHeight = 0
animFPS = 0
animAudio = None
animFrameDir = None

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

  def __init__(self, name, filename, x, y, scale, invert, crop):
    self.x = x
    self.y = y
    self.scale = scale
    self.name = name
    self.filename = filename
    self.crop = crop
    path = animFrameDir+"/"+filename
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
  
  def getCrop(self):
    return self.crop

  def isCorrect(self):
    return self.data and not self.data.isNull()


def fillDefaults(data, defaults):
  data.update(dict(defaults, **data))
  if not 'name' in data:
      print('ERROR: approached a segment without name', data)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Approached a segment without name!').exec_()
      return False
  if not 'from' in data:
      print('ERROR: approached a segment without from field', data)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Approached a segment without from field!').exec_()
      return False
  if not 'len' in data and not 'to' in data:
      print('ERROR: approached a segment without len nor to field', data)
      QMessageBox(QMessageBox.Critical, 'Incorrect segment', 'Approached a segment without len nor to field!').exec_()
      return False
  if not 'framelen' in data:
      data['framelen'] = 1
  if not 'filename' in data:
      data['filename'] = data['name']
  if not 'to' in data:
      data['to'] = data['from'] + data['len']
  if not 'len' in data:
      data['len'] = data['to'] - data['from'] + 1
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
      data['invert'] = False
  if not 'crop' in data:
      data['crop'] = None
  return True

seqends = None
seqs = None
frames = None

def loadFrameData():

  global seqs, seqends, frames, animWidth, animHeight, animFPS, animAudio, animFrameDir

  print("Loading frame data...")

  segmentlist.model().removeRows(0, segmentlist.model().rowCount())

  try:
    with open("jimi.yaml") as f:
      data = yaml.safe_load(f)
  except:
    print('ERROR: syntax error')
    QMessageBox(QMessageBox.Critical, 'Syntax error', 'Could not parse YAML file!').exec_()
    watcher.addPath("jimi.yaml")
    return False

  watcher.addPath("jimi.yaml")
  seqends = {}
  seqs = {}

  lastname = ""
  frames = []
  
  errorhappened = False
  
  animWidth = int(data["width"])
  animHeight = int(data["height"])
  animFPS = int(data["fps"])
  animAudio = data["audio"]
  animFrameDir = data['framedir']

  for i in range(0, int(data["length"])):
    frames.append([])
  
  for frameset in data["framesets"]:
    default = data.get("default")
    if not default:
      default = {}
    if frameset.get("inherit"):
      if frameset["inherit"] in seqs:
        default = dict(default, **seqs[frameset["inherit"]])
    if not fillDefaults(frameset, default):
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
    if "after" in frameset:
      if not frameset["after"]:
        startime = 0
      elif frameset["after"] in seqends:
        starttime = seqends[frameset["after"]]
      else:
        print('WARNING: segment', name, 'specified non-existent segment', frameset["after"], 'as its "after" field!')
        QMessageBox(QMessageBox.Warning, 'Incorrect after field', 'Segment ' + name + ' specified non-existent segment ' + str(frameset["after"]) + ' as its "after" field!').exec_()
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
      img = Frame(name, filename + str(frame).zfill(2) + ".png", frameset["x"], frameset["y"], frameset["scale"], frameset["invert"], frameset["crop"])
      if i > len(frames) - 1:
        frames.append([])
      frames[i].append(img)
      if not img.isCorrect():
        path = img.getPath()
        if path in imagecache:
          del imagecache[path]
        errorhappened = True
  
    seqends[name] = endtime
    seqs[name] = frameset
    lastname = name
    segmentlist.addItem(str(starttime) + "-" + str(endtime-1) + ": " + name)
    
  palette = QPalette()
  palette.setColor(QPalette.WindowText, QColor('black'))
  if errorhappened:
    print('WARNING: Some files/segments could not be loaded!')
    palette.setColor(QPalette.WindowText, QColor('red'))
  label.setPalette(palette)
    
  slider.setSingleStep(1000//animFPS)
  slider.setMaximum(max(seqends.values()) * 1000//animFPS + 1000)
  print("Frame data loaded!")

def drawFrame(frame):
  if frame > len(frames) - 1:
    frame = len(frames) - 1
  painter.fillRect( QRectF(0, 0, animWidth, animHeight), QColor('black'))
  for img in frames[frame]:
    painter.drawImage(QRect(QPoint(img.getX(), img.getY()), img.getSize()*img.getScale()), img.getImage())
  scene.clear()
  scene.addPixmap(pixmap)
  view.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
  label.setText('Frame ' + str(frame) + ' / ' + str(frames[frame]))
  for item in segmentlist.findItems('', Qt.MatchContains):
    segstart, segend = item.text().split(': ')[0].split('-')
    item.setSelected(False)
    if int(segstart) <= frame <= int(segend):
      item.setSelected(True)
      segmentlist.scrollToItem(item)

def advanceFrame():
    #global frameNr
    #frameNr += 1
    #print(frameNr)
    #drawFrame(frameNr)
    drawFrame(int(player.position() / 1000 / (1/animFPS)))

def playPause():
    if player.state() == QMediaPlayer.PlayingState:
        player.pause()
        timer.stop()
        button.setText("Play")
    else:
        player.play()
        timer.start(1000//60) # 50?
        button.setText("Pause")

def positionChanged():
    if not slider.isSliderDown():
        slider.setSliderPosition(player.position())

def sliderReleased():
    if player.position() != slider.sliderPosition() and slider.sliderPosition() != slider.maximum():
        player.setPosition(slider.sliderPosition())
    advanceFrame()

def segmentSelected(text):
    if not text:
      return
    start = int(text.split('-')[0])
    player.setPosition(start * 1000 * 1//25)


w = QMainWindow()
w.resize(1658, 854)
w.setWindowTitle('Jimi.pl Editor')

view = QGraphicsView()
button = QPushButton("Play")
button.clicked.connect(playPause)

slider = QSlider()
slider.setOrientation(Qt.Horizontal)
slider.valueChanged.connect(sliderReleased)

timer = QTimer()
timer.timeout.connect(advanceFrame)

scene = QGraphicsScene()

view.setScene(scene)

label = QLabel()

segmentlist = QListWidget()
segmentlist.setMaximumSize(QSize(350, 16777215))
segmentlist.setSelectionMode(QAbstractItemView.ExtendedSelection)
segmentlist.currentTextChanged.connect(segmentSelected)

vbox = QVBoxLayout()

hbox = QHBoxLayout()
hbox.addWidget(view)
hbox.addWidget(segmentlist)

vbox.addLayout(hbox)
vbox.addWidget(label)
vbox.addWidget(slider)
vbox.addWidget(button)
        
widget = QWidget()
widget.setLayout(vbox)    

loadFrameData()

url = QUrl.fromUserInput(animAudio, QDir.currentPath())
content = QMediaContent(url)
player = QMediaPlayer()
player.setMedia(content)
player.positionChanged.connect(positionChanged)

w.setCentralWidget(widget)

QTimer.singleShot(0, advanceFrame)

pixmap	= QPixmap (QSize(animWidth,animHeight))    
painter	= QPainter (pixmap)    
painter.fillRect( QRectF(0, 0, animWidth, animHeight), QColor('black'))
scene.addPixmap(pixmap)
scene.setSceneRect(QRectF(pixmap.rect()))

advanceFrame()

w.show()

sys.exit(app.exec_())
