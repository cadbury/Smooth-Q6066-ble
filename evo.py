from bluepy import btle
import binascii
import time,struct,datetime
from hexdump import hexdump

class CRC16():
	#crc16-xmodem
	def __init__(self):
		self.width = 16
		self.poly = 0x1021
		self.seed = 0
		self.xor = 0
		self.result_mask = (1 << self.width) - 1
		self.msb_lshift = self.width - 8
		self.table = self.getTable(self.poly, self.width)
		self.raw=''


	def getTable(self, poly, width):
		ms_bit = 1 << (width - 1)
		result_mask = (1 << width) - 1
		table = 256 * [0]
		crc = ms_bit

		i = 1
		while i <= 128:
			if crc & ms_bit:
				crc = (crc << 1) ^ poly
			else:
				crc <<= 1
			crc &= result_mask

			for j in range(0, i):
				table[i + j] = table[j] ^ crc
			i <<= 1
		return table


	def calc(self, data):
		data = bytearray(data)

		remainder = self.seed
		for value in data:
			remainder = ((remainder << 8) ^ self.table[(remainder >> self.msb_lshift) ^ value])
			remainder &= self.result_mask

		return struct.pack('>H', (remainder ^ self.xor))


	def verify(self, fullData):
		data = fullData[:5]
		self.raw = data

		crc = self.calc(data)

		if fullData[5] == crc[0] and fullData[6] == crc[1]:
			return True
		else:
			return False


class Evo(btle.DefaultDelegate):
	def __init__(self, deviceAddress):
		btle.DefaultDelegate.__init__(self)

		self.curCoords = b'\x00\x00'
		self.startCoords = b'\x0c\xfb'
		self.endCoords = b'\xf5\x1d'
		self.panStatus = ""

		self.peripheral = btle.Peripheral(deviceAddress, btle.ADDR_TYPE_PUBLIC)
		self.peripheral.setDelegate(self)

		for svc in self.peripheral.services:
			print str(svc)	

		self.service = self.peripheral.getServiceByUUID("0000fee9-0000-1000-8000-00805f9b34fb")	#Quintic 
		self.characteristic = self.service.getCharacteristics()

		for cha in self.characteristic:
			print str(cha)


		print "Notifications enabled"
		self.peripheral.writeCharacteristic(0x33, struct.pack('<BB', 0x01, 0x00), withResponse=True)
		self.peripheral.writeCharacteristic(0x30, struct.pack('<BB', 0x01, 0x00), withResponse=True)


		print "Device name:"
		hexdump(self.peripheral.readCharacteristic(0x0003))

		uuidWrite  = btle.UUID("d44bc439-abfd-45a2-b575-925416129600")	#44, 0x2C
		uuidRead  = btle.UUID("d44bc439-abfd-45a2-b575-925416129601")	#47, 0x2F
		uuid  = btle.UUID("d44bc439-abfd-45a2-b575-925416129610")		#50, 0x32

		self.chaWrite = self.service.getCharacteristics(uuidWrite)[0]
		self.chaRead = self.service.getCharacteristics(uuidRead)[0]
		self.cha = self.service.getCharacteristics(uuid)[0]

	def cmd(self, data, wait_for=5.0):
		newData = b''

		for x in range(0, len(data), 5):
			temp = data[x:x+5]
			crc = CRC.calc(temp)
			newData += temp + crc


		self.chaWrite.write(newData)
		print '<- Sent:', 
		hexdump(newData)
		self.waitForNotifications(wait_for)

	def move_up(self):
		self.cmd(b'\x06\x10\x01\x01\x2c')

	def move_down(self):
		self.cmd(b'\x06\x10\x01\x0e\xd4')

	def move_left(self):
		self.cmd(b'\x06\x10\x02\x01\x2c')		

	def move_right(self):
		self.cmd(b'\x06\x10\x02\x0e\xd4')		

	def set_mode_pan_follow(self):
		self.cmd(b'\x06\x81\x27\x00\x00')		

	def set_mode_follow(self):
		self.cmd(b'\x06\x81\x27\x00\x02')	

	def set_mode_locking(self):
		self.cmd(b'\x06\x81\x27\x00\x01')	

	def get_mode(self):
		self.cmd(b'\x06\xc1\x31\x00\x01')

	def get_power(self):
		self.cmd(b'\x06\x01\x06\x00\x00')

	def get_model(self):
		self.cmd(b'\x06\x01\x02\x00\x00')

	def get_firmware(self):
		self.cmd(b'\x06\x01\x04\x00\x00')

	def get_reverse(self):
		self.cmd(b'\x06\x01\x67\x00\x00')

	def get_coords(self):
		self.cmd(b'\x06\x01\x22\x00\x00\x06\x01\x24\x00\x00')

	def set_restore(self):
		self.cmd(b'\x06\xc1\x21\x00\x00')

	def set_reverse(self):
		self.cmd(b'\x06\xc1\x21\x00\x01')

	def set_stop(self):
		self.cmd(b'\x06\x81\x07\x00\x00')

	def set_start(self):
		self.cmd(b'\x06\x81\x07\x00\x01')

	def set_pan_start(self):
		self.get_coords()
		self.startCoords = self.curCoords

	def set_pan_end(self):
		self.get_coords()
		self.endCoords = self.curCoords

	def start_pan(self):

		self.set_mode_locking()


		self.cmd(b'\x06\xc1\x30\x00\x01')		#begin pan entry
		self.cmd(b'\x06\xc1\x31\x00\x00')		#begin params
		self.cmd(b'\x06\xc1\x37\x00\x00\x06\xc1\x36\x00\x00')		#0ms
		self.cmd(b'\x06\xc1\x33' + self.startCoords[0] + b'\x1c')						#pos1
		self.cmd(b'\x06\xc1\x35' + self.startCoords[1] + b'\x1c')						#pos2

		self.cmd(b'\x06\xc1\x31\x00\x01')		#end params
		self.cmd(b'\x06\xc1\x30\x00\x00')		#end pan entry




		self.cmd(b'\x06\xc1\x30\x00\x01')		#begin pan entry
		self.cmd(b'\x06\xc1\x31\x00\x00')		#begin params

		self.cmd(b'\x06\xc1\x37\x00\x00\x06\xc1\x36\x75\x30')		#3000ms
		self.cmd(b'\x06\xc1\x33' + self.endCoords[0] + b'\x1c')							#pos1
		self.cmd(b'\x06\xc1\x35' + self.endCoords[1] + b'\x1c')							#pos2

		self.cmd(b'\x06\xc1\x31\x00\x01')		#end params


		while self.panStatus != "done":
			self.cmd(b'\x06\xc1\x32\x00\x00')		#status
			time.sleep(0.2)




	def decode(self, handle, data):
		if ord(data[0]) == 0x06:
			print "Data,",
		else:
			hexdump(data)
			return


		if ord(data[1]) == 0x01:
			print "Query,",	
		elif ord(data[1]) == 0x81:
			print "Set,",
		elif ord(data[1]) == 0x10:
			print "Move,",
			if ord(data[2]) == 0x01 and ord(data[3]) == 0x01:
				print "up"
			elif ord(data[2]) == 0x01 and ord(data[3]) == 0x0e:
				print "down"
			elif ord(data[2]) == 0x02 and ord(data[3]) == 0x01:
				print "left"
			elif ord(data[2]) == 0x02 and ord(data[3]) == 0x0e:
				print "right"

			return
		elif ord(data[1]) == 0xc1:
			print "Other,",
			if ord(data[2]) == 0x21:
				print "restore?"
			elif ord(data[2]) == 0x32:
				status = {
					0x52: "busy",
					0x04: "complete",
					0x42: "done"
				}
				self.panStatus = status[ord(data[4])]
				print "Status:", self.panStatus
			elif ord(data[2]) == 0x36:
				print "time: ", (ord(data[3])<<8 | ord(data[4]))
			else:
				print "unknown"

			return

		if ord(data[2]) == 0x04:
			print "Firmware: ", ord(data[4])
		elif ord(data[2]) == 0x02:
			print "Model: ", ord(data[3]) | (ord(data[4])<<8)
		elif ord(data[2]) == 0x06:
			print "Power?: ", ord(data[4]) | (ord(data[3])<<8)
		elif ord(data[2]) == 0x07:
			print "Enabled: ", ("Off" if ord(data[4]) == 0 else "On")
		elif ord(data[2]) == 0x22:
			print "X: ", ord(data[3]), ord(data[4])
			self.curCoords[0] = ord(data[3])
		elif ord(data[2]) == 0x24:
			print "Y: ", ord(data[3]), ord(data[4])
			self.curCoords[1] = ord(data[3])
		elif ord(data[2]) == 0x64:
			print "PTZ Ctrl: T", (ord(data[3])<<8 | ord(data[4])) /100
		elif ord(data[2]) == 0x65:
			print "PTZ Ctrl: R", (ord(data[3])<<8 | ord(data[4])) /100
		elif ord(data[2]) == 0x66:
			print "PTZ Ctrl: P", (ord(data[3])<<8 | ord(data[4])) /100

		elif ord(data[2]) == 0x67:
			print "PTZ Reverse: T", ("1" if ord(data[4]) & 0x01 else "0"), "R:", ("1" if ord(data[4]) & 0x02 else "0"), "P:",("1" if ord(data[4]) & 0x04 else "0")

		elif ord(data[2]) == 0x5b:
			print "PTZ Dead: T", (ord(data[3])<<8 | ord(data[4])) /10
		elif ord(data[2]) == 0x5c:
			print "PTZ Dead: R", (ord(data[3])<<8 | ord(data[4])) /10
		elif ord(data[2]) == 0x5d:
			print "PTZ Dead: P", (ord(data[3])<<8 | ord(data[4])) /10

		elif ord(data[2]) == 0x5e:
			print "PTZ Roll: T", (ord(data[3])<<8 | ord(data[4])) /100
		elif ord(data[2]) == 0x5f:
			print "PTZ Roll: R", (ord(data[3])<<8 | ord(data[4])) /100
		elif ord(data[2]) == 0x60:
			print "PTZ Roll: P", (ord(data[3])<<8 | ord(data[4])) /100
		elif ord(data[2]) == 0x27:
			modes = {
				0: "Pan Follow",
				1: "Locking",
				2: "Following"
			}
			print "Mode", modes[ord(data[4])]
		elif ord(data[2]) == 0x21:
			print "Reverse?", ("On" if ord(data[4]) == 0 else "Off")
		else:
			print "unknown"



	def decodeButton(self, data):
		buttons = {
			54: "Shutter",
			55: "T",
			56: "W",
			71: "T long",
			39: "T long rel",
			72: "W long",
			40: "T long rel"
		}

		if ord(data[3]) in buttons:
			print 'Button: ', buttons[ord(data[3])]
		else:
			hexdump(data)


	def handleNotification(self, cHandle, data):
		if cHandle == 0x32:
			self.decodeButton(data)
			return

		#data can be 7 or 14 bytes
		for x in range(0, len(data), 7):
			temp = data[x:x+5]
			crc = CRC.verify(data)

			if crc is True:
				self.decode(cHandle, temp)
			else:
				print "CRC bad"


	def waitForNotifications(self, time):
		self.peripheral.waitForNotifications(time)


	def disconnect(self):
		self.peripheral.disconnect()

if __name__ == '__main__':
	CRC = CRC16()

	e = Evo('ac:9a:22:3a:85:0d')

	try:
		e.get_power()
		while True:
			#e.get_coords()
			#e.move_right()

			if e.waitForNotifications(1.0):
				print("Notification")
				continue
		print("Waiting")
	finally:
		e.disconnect()
		print ("Disconnected")











