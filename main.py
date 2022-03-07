from telethon import events
from os import getenv
from dotenv import load_dotenv
from telethon.sync import TelegramClient
import os
import asyncio
import ffmpeg
from FastTelethonhelper import fast_download, fast_upload
import logging
import subprocess

API_ID= int(getenv("API_ID"))
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)

logger = logging.getLogger("__name__")

def subp(cmd):
  result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  f = open('log.txt', 'w')
  f.write(str(result))
  f.close()
  return result


def convert_video(chat_id, input_type, output_type):

	"""

	The function converts video of one type to another.

	Args:

		chat_id: unique identification for video

		input_type: video input type

		output_type: video output type

	"""

	inputs = {'./input_media/{}.{}'.format(chat_id, input_type): None}

	if output_type == "gif":

		outputs = {'./output_media/{}.{}'.format(chat_id, output_type): '-t 3 -vf "fps=30,scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0'}

	else:

		outputs = {'./output_media/{}.{}'.format(chat_id, output_type): None}

	ff = ffmpy.FFmpeg(

	    inputs=inputs,

	    outputs=outputs

	)

	ff.run()

	return None 

def generate_thumbnail(in_filename):
    probe = ffmpeg.probe(in_filename)
    out_filename = f'{in_filename[:-3]}.jpg'
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", in_filename]
    time = float(subp(cmd).stdout.decode())
    time = time // 2
    width = probe['streams'][0]['width']
    try:
        (
          ffmpeg
          .input(in_filename, ss=time)
          .filter('scale', width, -1)
          .output(out_filename, vframes=1)
          .overwrite_output()
          .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(e.stderr.decode())
    return out_filename

def vidsticker(in_filename):
  out_filename =f'{in_filename[:-3]}_processed.webm'
  try:
    (
      ffmpeg.
      input(in_filename)
      .output(out_filename, vcodec='libvpx-vp9', crf=40, pix_fmt='yuva420p', vf='scale=512:-1')
      .global_args('-report')
      .run()
    )
  except ffmpeg.Error as e:
     print(e.stderr.decode())
  return out_filename
  
@bot.on(events.NewMessage(pattern=r'/vs'))
async def stickervid(event):
  video = await event.get_reply_message()
  if video.file.duration > 3:
    return await event.reply('Should be smaller than 3 secs as per Telegram video-sticker guideline.')
  m = await event.reply('Downloading...')
  dl = await fast_download(bot, video)
  await m.edit('Encoding....')
  hek = vidsticker(dl)
  await m.edit('Uploading...')
  fu = await fast_upload(bot, hek)
  await bot.send_message(event.chat_id, file = fu, force_document=True)
  await m.delete()
  os.remove(dl)
  os.remove(hek)  

@bot.on(events.NewMessage(pattern=r'ffmpeg'))
async def ffmpegr(event):
  try:
    stcmd = event.text.split(' ')
  except IndexError:
    return await event.reply('Use as ffmpeg <cmd>')
  video = await event.get_reply_message()
  m = await event.reply('Downloading...')
  dl = await fast_download(bot, video)
  out = f'{dl[:-4]}_ffmpeg.{stcmd[-1]}'
  await m.edit('Encoding....')
  #cmd = f'ffmpeg -i {dl} {stcmd} {out}'
  stcmd.pop(0)
  stcmd.pop(-1)
  cmd = ['ffmpeg', '-i', dl]
  cmd.extend(stcmd)
  cmd.append('-y')
  cmd.append(f'{out}')
  await event.reply(" ".join(cmd))
  h = subp(cmd)
  #await event.reply(str(h))
  await m.edit('Uploading.....')
  await bot.send_message(event.chat_id, video=out, thumb=generate_thumbnail(dl))
  await m.delete()

@bot.on(events.NewMessage(pattern=r'/log'))
async def log_send(event):
  try:
    await event.reply(file='log.txt')
  except Exception as e:
    pass

@bot.on(events.NewMessage(pattern=r'/start'))
async def start(event):
  if event.is_private:
    await event.reply('Yo!\nThings i can do:\n1) /vs : Convert videos to webm (telegram video sticker format)\n2) ffmpeg: reply to a file and then write the ffmpeg command as **ffmpeg <cmds> <output extension>**\n3) /log : To get the last ffmpeg log')

print('Starting...')
bot.start() 
print('Bot started!')
bot.run_until_disconnected()  
