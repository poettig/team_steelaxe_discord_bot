import argparse
import json
import logging
import threading

from discord_client import DiscordClient, DiscordClientConfig
from message_scheduler import MessageScheduler


def setup_logging(verbose: bool, debug: bool):
	if debug:
		log_level = logging.DEBUG
	elif verbose:
		log_level = logging.INFO
	else:
		log_level = logging.WARNING

	log_format = "[%(asctime)s] %(levelname)8s: %(message)s"
	log_date_format = "%Y-%m-%d %H:%M:%S"

	logging.basicConfig(level=log_level, format=log_format, datefmt=log_date_format)


def main():
	parser = argparse.ArgumentParser(
		description="Allows to subscribe for discord notification messages on multiple twitch stream state changes."
	)
	parser.add_argument("--verbose", "-v", action="store_true", help="Enable informational output.")
	parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output.")
	parser.add_argument(
		"--config-path", "-c", default="config.json",
		help="The path to the configuration file, default is 'config.json' in the current working directory."
	)
	parser.add_argument(
		"--scheduled-messages-path", "-s", default="scheduled_messages.yml",
		help=(
			"The path to the YAML file containing the scheduled messages,"
			" default is 'scheduled_messages.yml' in the current working directory."
		)
	)
	args = parser.parse_args()

	setup_logging(args.verbose, args.debug)

	with open(args.config_path, "r") as fh:
		config = json.load(fh)

	discord_config = DiscordClientConfig(config.get("reaction_roles"))
	discord_client = DiscordClient(config.get("discord_bot_token"), discord_config)
	discord_thread = threading.Thread(target=discord_client.start)
	discord_thread.start()

	message_scheduler = MessageScheduler(args.scheduled_messages_path, discord_client)
	message_scheduler_thread = threading.Thread(target=message_scheduler.start)
	message_scheduler_thread.start()

	discord_thread.join()
	message_scheduler_thread.join()


if __name__ == "__main__":
	main()
