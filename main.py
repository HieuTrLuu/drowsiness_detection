from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.core.image import Image
from kivy.uix.image import AsyncImage
from kivy.uix.button import Button
from kivy.core.window import Window

from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.texture import Texture
from kivy.garden.graph import Graph, MeshStemPlot
from kivy.animation import Animation
from kivy.logger import Logger

from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '500')
Config.set('graphics', 'minimum_width', '400')
Config.set('graphics', 'minimum_height', '300')

import cv2
import json
from time import time
from queue import Queue
from threading import Thread
from numpy import array

import logging.config
from logger import logger_config

import video_main
from config_params import ConfigParams

logging.config.dictConfig(logger_config)
logger = logging.getLogger('app_logger')

class Container(BoxLayout):
	def __init__(self, **kwargs):
		super(Container, self).__init__(**kwargs)

		self.fps = 0
		self.alarm_state = False
		self.sound_state = False

		# data to plotting
		self.plot = MeshStemPlot(color=[.4, 1, 0, 1])
		self.arr_size = 100
		self.counter = self.arr_size
		
		self.xx = [i for i in range(self.arr_size)]
		self.yy = [ .4 for i in range(self.arr_size)]
		self.arr = self.yy
		
		zipped = zip(self.xx, self.arr)
		self.points = []
		for i in zipped:
			self.points.append(i)
		self.plot.points = self.points
		self.link_to_graph.add_plot(self.plot)
		# Ox axis
		self.plot_axis = MeshStemPlot(color=[1, 1, 1, 1])
		self.plot_axis.points = [(0, 0), (100, 0)]
		self.link_to_graph.add_plot(self.plot_axis)

		# big logo
		fake_array = array([1,1,1,3])
		# convert image to texture
		buf = cv2.flip(fake_array, 0).tostring()
		image_texture = Texture.create(size=(1, 1), colorfmt='bgr')
		image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
		self.main_image_texture4 = image_texture

		self.cameras_list = ['First camera']

	def set_queue(self, frames_queue):
		self.frames_queue = frames_queue

	def set_stream(self, stream):
		self.stream = stream

	def set_cameras(self, cameras):
		self.cameras = cameras

	def play_sound(self, wav_file='alarm.wav'):
		if not self.sound_state:
			self.sound_state = True
			try:
				sound = SoundLoader.load('data/alarm.wav')
			except:
				pass
			sound.bind(on_stop=self.on_sound_stopped)
			sound.play()

	def on_sound_stopped(self, instance):
		self.sound_state = False

	def on_slider_ear(self, value):
		self.stream.ear_threashold = float(value)

	def on_slider_quality(self, value):
		self.stream.reduce_image = value / 100

	def on_slider_delay(self, value):
		self.stream.seconds_to_detect_drowsiness = value

	def on_input_attentiveness(self, value, angle, position):
		try:
			value = float(value)
			if position == 'bot':
				self.stream.attentive_dict[angle][0]= float(value)
			elif position == 'top':
				self.stream.attentive_dict[angle][1]= float(value)
		except:
			print('incorrect type casting')

	def on_show_video(self, value):
		if value == 'Show video':
			self.link_to_btn_show_video.text = 'Hide video'
			self.stream.show_video = True
		else:
			self.link_to_btn_show_video.text = 'Show video'
			self.stream.show_video = False

			self.link_to_image.texture = self.main_image_texture
	
	def on_spinner_clicked(self, value): 
		print(f"Face detection algorithm is {value}" ) 
		# self.stream.select_algo = value

	def on_checkbox_click(self, value):
		self.stream.overlay_bool = value
		
	def on_checkbox_attention_click(self, value):
		self.stream.check_attention = value
   

	def transfer_frame(self):
		qsize = self.frames_queue.qsize()
		self.alarm_state = False
		for ii in range(qsize):
			(alarm_state, self.fps, ear, self.image, head_pose) = self.frames_queue.get()

			# self.link_to_label_head_pose.text = 'head pose: ' + f"{head_pose[0]:.4f}"
			self.link_to_label_yaw.text =  f"yaw: {head_pose[0]:.2f}"
			self.link_to_label_pitch.text = f"pitch: {head_pose[1]:.2f}"
			self.link_to_label_row.text = f"row: {head_pose[2]:.2f}"

			self.link_to_label_ear.text = f"ear: {ear:.4f}"
			self.alarm_state = self.alarm_state or alarm_state

			# refresh graph
			delta = ear - self.link_to_slider_eyes_tuner.value
			self.yy[self.counter % self.arr_size] = delta
			self.counter += 1
			self.arr = self.yy[(self.counter % self.arr_size):] + self.yy[:(self.counter % self.arr_size)]

			zipped = zip(self.xx, self.arr)
			self.points = []
			for i in zipped:
				self.points.append(i)

		# refresh just last fps
		self.link_to_label_fps.text = 'fps: ' + str(self.fps)

		# refresh graph (bunch)
		self.plot.points = self.points
		# refrresh self.alarm_state (bunch)

		if self.alarm_state['drowsy']:
			print('in drowsy loop')
			self.play_sound()
			self.link_to_alert_drowsy.canvas.children[0].rgb = [.7, 0, 0]
			self.link_to_layout.canvas.children[0].rgb = [.7, 0, 0]
		else:
			self.link_to_alert_drowsy.canvas.children[0].rgb = [0, 0, 0]
			self.link_to_layout.canvas.children[0].rgb = [0, 0, 0]


		
		if self.alarm_state['inattentive']:
			print('in attentive loop')
			self.play_sound()
			self.link_to_alert_inattentive.canvas.children[0].rgb = [.7, 0, 0]
			# self.link_to_alert_drowsy.canvas.children[0].rgb = [.7, 0, 0]
		else:
			self.link_to_alert_inattentive.canvas.children[0].rgb = [0, 0, 0]
			# self.link_to_layout.canvas.children[0].rgb = [0, 0, 0]
			# self.link_to_alert_drowsy.canvas.children[0].rgb = [0, 0, 0]

		# show just last frame	

		try:
			if self.link_to_btn_show_video.text == 'Hide video':
				# convert image to texture
				buf = cv2.flip(self.image, 0).tostring()
				image_texture = Texture.create(size=(self.image.shape[1], self.image.shape[0]), colorfmt='bgr')
				image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
				self.link_to_image.texture = image_texture
		except:
			pass

	def on_start(self):
		if self.link_to_start_stop.text == 'Start':
			camera_num = self.cameras_list.index(self.link_to_btn_camera.text)
			self.stream.start(camera_num)
			self.link_to_start_stop.text = 'Stop'
		else:
			self.stream.stop()
			self.link_to_start_stop.text = 'Start'

	def apply_params(self, btn_camera, btn_show_video, slider_delay
					, slider_quality, slider_eyes_tuner, alarm_file, image
					):
		self.link_to_btn_camera.text = btn_camera
		self.link_to_btn_show_video.text = btn_show_video
		self.link_to_slider_delay.value = slider_delay 
		self.link_to_slider_quality.value = slider_quality
		self.link_to_slider_eyes_tuner.value = float(slider_eyes_tuner)
		self.link_to_image.source = image
		self.alarm_file = alarm_file

class DrowsinessApp(App):
	def build(self):
		logger.info('Enter in to the build()')
		
		# common queue
		frames_queue = Queue(maxsize=0)

		self.load_configuration()
		
		self.stream = video_main.VideoMain()

		try:
			self.stream.init_tools(	  shape_predictor='data/shape_predictor_68_face_landmarks.dat'
									, frames_queue=frames_queue
									, ear_threashold=self.config.data[0]['ear_threashold']
									, reduce_image=self.config.data[0]['reduce_image']
									, show_video=self.config.data[0]['show_video']
									, seconds_to_detect_drowsiness=self.config.data[0]['seconds_to_detect_drowsiness']
									, frames_to_calculate_fps=self.config.data[0]['frames_to_calculate_fps'])
		except:
			logger.info('could not init_tools for stream; raise exception')
			raise ValueError('could not init_tools for stream')

		self.detect_on_start = self.config.data[0]['detect_on_start']
		self.cameras = video_main.VideoMain.get_registered_cameras()
		logger.info('registered cameras {}'.format(self.cameras))

		self.active_camera = 0 if len(self.cameras) else -1

		if self.active_camera == -1:
			logger.info('could not capture camera; raise exception')
			raise ValueError('could not capture camera')
		
		self.container = Container()
		self.container.set_cameras(self.cameras)
		self.container.set_stream(self.stream)

		# show_video_title = 'Hide video' if self.config.data[0]['show_video'] else 'Show video'		
		# if self.config.data[0]['detect_on_start'] == 0:
		show_video_title = 'Hide video'
		self.container.apply_params(  btn_camera='First camera'
									, btn_show_video=show_video_title
									, slider_delay=self.config.data[0]['seconds_to_detect_drowsiness']
									, slider_quality=self.config.data[0]['reduce_image'] * 100
									, slider_eyes_tuner=self.config.data[0]['ear_threashold']
									, alarm_file=self.config.data[0]['wav_file']
									, image='img/big_logo.png')
		self.container.set_queue(frames_queue)
		# 
		event = Clock.schedule_interval(self.callback_check_queue, 1 / 10.)
		#
		if self.detect_on_start:
			self.stream.start(self.active_camera)
			self.container.link_to_start_stop.text = 'Stop'
		
		self.icon = 'img/drowsy1.png'

		logger.info('Return build()')
		return self.container

	def callback_check_queue(self, dt):
		try:
			self.container.transfer_frame()
		except:
			print('vvv')

	def load_configuration(self):
		self.config = ConfigParams()

	def on_stop(self):
		self.config.data[0]['camera'] = self.active_camera
		self.config.data[0]['ear_threashold'] = self.stream.ear_threashold
		self.config.data[0]['reduce_image'] = self.stream.reduce_image

		state_txt = self.container.link_to_btn_show_video.text
		state_int = 1 if state_txt == 'Hide video' else 0
		self.config.data[0]['show_video'] = state_int

		self.config.data[0]['seconds_to_detect_drowsiness'] = self.stream.seconds_to_detect_drowsiness

		state_txt = self.container.link_to_start_stop.text
		state_int = 1 if state_txt == 'Stop' else 0
		self.config.data[0]['detect_on_start'] = state_int

		self.config.config_save(file='config.json')
		
		if self.container.link_to_start_stop.text == 'Stop':
			self.stream.stop()
		
		logger.info('APPLICATION STOPPED')

		return True

if __name__ == "__main__":
	logger.info('\t---\tSTART APPLICATION\t---')	# custom logger
	Logger.info('Drowsiness\t: START APPLICATION')	# kivy logger
	try:
		DrowsinessApp().run()
	except:
			logger.info('could not run Drowsiness application')