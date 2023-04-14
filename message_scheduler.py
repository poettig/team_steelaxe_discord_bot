import os.path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import yaml

from discord_client import DiscordClient


class MessageScheduler:
	def __init__(self, scheduled_message_file: str, discord_client: DiscordClient):
		if not os.path.isfile(scheduled_message_file):
			raise ValueError("The file with the scheduled messages does not exist.")

		with open(scheduled_message_file, 'r') as fh:
			self.scheduled_messages = yaml.safe_load(fh)

		self.discord_client = discord_client

	def start(self):
		scheduler = BlockingScheduler()

		for scheduled_message in self.scheduled_messages:
			scheduler.add_job(
				self.send_discord_message,
				trigger=CronTrigger.from_crontab(scheduled_message["cron"]),
				args=[scheduled_message["message"], scheduled_message["channel_id"]]
			)

		scheduler.start()

	def send_discord_message(self, message: str, channel_id: int):
		channel = self.discord_client.client.get_channel(channel_id)
		self.discord_client.client.loop.create_task(channel.send(message))
