import json
import os
import threading
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask

# 1. 开启一个极简 Web 服务应付 Render 免费检测
app = Flask('')


@app.route('/')
def home():
  return 'Discord Bot is Running Live!'


def run_web():
  # 读取 Render 自动分配的 PORT，默认 8080
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()


# 2. Discord Bot 主体代码
intents = discord.Intents.default()
intents.message_content = True

DATA_FILE = 'thread_attachments.json'


def load_data():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
      return json.load(f)
  return {}


def save_data(data):
  with open(DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


class MyBot(commands.Bot):

  def __init__(self):
    super().__init__(command_prefix='!', intents=intents)

  async def setup_hook(self):
    await self.tree.sync()
    print('所有斜杠命令已成功同步！')


bot = MyBot()


@bot.event
async def on_ready():
  print(f'Bot 已成功登录，当前身份: {bot.user}')


# /保存附件
@bot.tree.command(
    name='保存附件', description='[帖主专享] 保存一个附件供其他成员下载'
)
@app_commands.describe(file='请选择需要保管的附件文件')
async def save_attachment_slash(
    interaction: discord.Interaction, file: discord.Attachment
):
  await interaction.response.defer(ephemeral=True)

  if not isinstance(interaction.channel, discord.Thread):
    await interaction.followup.send('请在具体的帖子/子区内使用此命令！')
    return

  thread = interaction.channel

  if thread.owner_id and interaction.user.id != thread.owner_id:
    await interaction.followup.send(
        '抱歉，只有本帖的楼主（帖主）可以保存附件！'
    )
    return

  thread_id = str(thread.id)
  data = load_data()

  if thread_id not in data:
    data[thread_id] = {
        'thread_name': thread.name,
        'owner_id': interaction.user.id,
        'files': [],
    }

  data[thread_id]['files'].append({'name': file.filename, 'url': file.url})
  save_data(data)

  await interaction.followup.send(
      f'已成功保存附件 **{file.filename}**！目前本帖共有'
      f" {len(data[thread_id]['files'])} 个附件。其他成员输入 `/获取附件`"
      ' 即可获取。'
  )


# /获取附件
@bot.tree.command(
    name='获取附件', description='获取帖主在此帖子中保存的所有附件'
)
async def get_attachment_slash(interaction: discord.Interaction):
  await interaction.response.defer()

  if not isinstance(interaction.channel, discord.Thread):
    await interaction.followup.send('请在具体的帖子/子区内使用此命令！')
    return

  thread_id = str(interaction.channel.id)
  data = load_data()

  if thread_id not in data or not data[thread_id]['files']:
    await interaction.followup.send('该帖子暂无帖主保管的附件。')
    return

  files = data[thread_id]['files']
  reply_lines = [f'**【{interaction.channel.name}】帖主附件列表：**']
  for idx, item in enumerate(files, 1):
    reply_lines.append(f"{idx}. [{item['name']}]({item['url']})")

  await interaction.followup.send('\n'.join(reply_lines))


# 启动 Web 服务和 Bot
if __name__ == '__main__':
  keep_alive()
  bot.run(os.getenv('DISCORD_TOKEN'))