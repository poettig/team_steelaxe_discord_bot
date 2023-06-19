import io
import logging
import re
import typing
import discord
import prettytable


class DiscordClientConfig:
	REACTION_ROLE_KEYS = [
		"emoji",
		"message-id",
		"role-id"
	]

	def __init__(self, reaction_roles: typing.List[typing.Dict]):
		if not reaction_roles or not isinstance(reaction_roles, list):
			raise ValueError("Reaction roles has to be a list of dicts.")

		for reaction_role in reaction_roles:
			if (
				not isinstance(reaction_role, dict)
				or any(key not in DiscordClientConfig.REACTION_ROLE_KEYS for key in reaction_role.keys())
			):
				raise ValueError(f"Reaction role has to be a dict containing {', '.join(DiscordClientConfig.REACTION_ROLE_KEYS)}")

			if isinstance(reaction_role["emoji"], str) and reaction_role["emoji"].isdigit():
				raise ValueError(f"The emoji ID for the custom emoji {reaction_role['emoji']} has to be an int in the config.")

		self.reaction_roles = reaction_roles
		self.by_message_id = {reaction_role["message-id"]: reaction_role for reaction_role in reaction_roles}


class DiscordClient:
	def __init__(self, discord_bot_token: str, discord_config: DiscordClientConfig):
		intents = discord.Intents.default()
		intents.guilds = True
		intents.members = True
		intents.reactions = True

		self.config = discord_config
		self.client = discord.Client(intents=intents)
		self.discord_bot_token = discord_bot_token
		self.command_tree = discord.app_commands.CommandTree(self.client)
		self.role_cache = dict()

		@self.client.event
		async def on_ready():
			await self.command_tree.sync()
			logging.info(f"Bot is now logged in as {self.discord_user_to_full_name(self.client.user)}")

		@self.client.event
		async def on_raw_reaction_add(reaction):
			await self._on_raw_reaction(reaction)

		@self.client.event
		async def on_raw_reaction_remove(reaction):
			await self._on_raw_reaction(reaction)

		@self.client.event
		async def on_guild_role_create(role: discord.Role):
			await self._update_role_cache(role.guild)

		@self.client.event
		async def on_guild_role_delete(role: discord.Role):
			await self._update_role_cache(role.guild)

		@self.command_tree.command(
			name="count-members",
			description="Gets a count members in a role for all roles or the role that was given."
		)
		async def count_members(interaction, role: str = None):
			await self._count_members(interaction, role)

		@count_members.autocomplete("role")
		async def count_members_autocomplete(interaction, current):
			return await self._count_members_autocomplete(interaction, current)

	def start(self):
		self.client.run(self.discord_bot_token, log_handler=None)

	def _get_reaction_role_by_message(self, reaction: discord.RawReactionActionEvent) -> typing.Optional[dict]:
		return self.config.by_message_id.get(reaction.message_id, None)

	@staticmethod
	def _check_emoji(emoji: discord.PartialEmoji, reaction_role: dict):
		unicode_emoji_matches = emoji.is_unicode_emoji() and emoji.name == reaction_role["emoji"]
		custom_emoji_matches = emoji.is_custom_emoji() and emoji.id == reaction_role["emoji"]

		return unicode_emoji_matches or custom_emoji_matches

	def _get_member_from_reaction(
		self,
		reaction: discord.RawReactionActionEvent
	) -> typing.Tuple[typing.Optional[discord.Guild], typing.Optional[discord.Member]]:
		guild = self.client.get_guild(reaction.guild_id)
		if not guild:
			logging.error("Guild for reacting member not found.")
			return None, None

		member = guild.get_member(reaction.user_id)
		if not member:
			logging.error("User that added the reaction was not found.")
			return None, None

		return guild, member

	def _get_message_from_reaction(
		self,
		reaction: discord.RawReactionActionEvent
	) -> typing.Optional[typing.Coroutine[typing.Any, typing.Any, discord.Message]]:
		channel = self.client.get_channel(reaction.channel_id)
		if not channel:
			logging.error("Could not fetch channel from reaction.")
			return

		try:
			return channel.fetch_message(reaction.message_id)
		except discord.NotFound:
			logging.error("Message for reaction not found.")
			return
		except discord.Forbidden:
			logging.error("Not allowed to get the message for this reaction.")
			return
		except discord.HTTPException as e:
			logging.error(f"Failed fetching message for reaction: {e}")
			return

	async def _update_role_cache(self, guild: discord.Guild):
		prev_role_count = len(self.role_cache.get(guild.id, []))

		roles = await guild.fetch_roles()
		self.role_cache[guild.id] = roles

		logging.info(f"Updated role cache, previously {prev_role_count}, now {len(self.role_cache.get(guild.id, []))} roles.")

	async def _count_members(self, interaction: discord.Interaction, role_name: str = None):
		result_table = prettytable.PrettyTable()
		result_table.field_names = ["Role Name", "Member Count"]
		result_table.align["Role Name"] = "l"
		result_table.align["Member Count"] = "r"

		logging.info(
			f"Member {DiscordClient.discord_user_to_full_name(interaction.user)} asked for the member count of"
			f" {'all roles' if role_name is None else 'role ' + role_name}."
		)

		if not self.role_cache or not self.role_cache.get(interaction.guild_id):
			await self._update_role_cache(interaction.guild)

		if len(self.role_cache) == 0:
			await interaction.response.send_message("There are no roles on this server.")
			return

		if not role_name:
			for role in self.role_cache.get(interaction.guild_id, []):
				result_table.add_row([
					role.name.replace("@", ""),
					len(role.members)
				])

			message = result_table.get_string(sortby='Member Count', reversesort=True)
			if len(message) >= 2000:
				with io.BytesIO() as f:
					f.write(message.encode())
					f.flush()
					f.seek(0)
					await interaction.response.send_message(file=discord.File(fp=f, filename="result.txt"))
			else:
				await interaction.response.send_message(f"```\n{message}\n```")

			return

		role_name_sanitized = role_name.replace("@", "")

		filtered_roles = list(filter(lambda r: r.name == role_name, self.role_cache.get(interaction.guild_id, [])))
		if len(filtered_roles) == 0:
			await interaction.response.send_message(f"There is no role with the name '{role_name_sanitized}' on this server.")
			return

		role = filtered_roles[0]
		await interaction.response.send_message(f"The role {role_name_sanitized} has {len(role.members)} members.")

	async def _count_members_autocomplete(self, interaction: discord, current: str):
		if not self.role_cache or not self.role_cache.get(interaction.guild_id):
			await self._update_role_cache(interaction.guild)

		choices = []
		for role in self.role_cache.get(interaction.guild.id):
			role_name_sanitized = re.sub(r"@", r"", role.name)
			if current.lower() in role.name.lower():
				choices.append(discord.app_commands.Choice(name=role_name_sanitized, value=role.name))

		return choices

	async def _on_raw_reaction(self, reaction: discord.RawReactionActionEvent):
		reaction_role = self._get_reaction_role_by_message(reaction)
		if not reaction_role:
			logging.debug(f"No reaction role found for message {reaction.message_id}.")
			return

		guild, member = self._get_member_from_reaction(reaction)
		if not guild or not member:
			return

		member_name = self.discord_user_to_full_name(member)

		if not self._check_emoji(reaction.emoji, reaction_role):
			if reaction.event_type == "REACTION_ADD":
				logging.info("Incorrect emoji used.")
				message = await self._get_message_from_reaction(reaction)
				if message:
					await message.remove_reaction(reaction.emoji, member)
					logging.info("Removed incorrect reaction.")
				else:
					logging.error("Could not remove incorrect reaction.")

			return

		if "role" not in reaction_role:
			reaction_role["role"] = guild.get_role(reaction_role["role-id"])

		try:
			if reaction.event_type == "REACTION_ADD":
				await member.add_roles(reaction_role["role"])
				logging.info(f"Successfully added role {reaction_role['role'].name} to member {member_name}.")
			elif reaction.event_type == "REACTION_REMOVE":
				await member.remove_roles(reaction_role["role"])
				logging.info(f"Successfully removed role {reaction_role['role'].name} from member {member_name}.")
			else:
				logging.error(f"Unexpected reaction event type {reaction.event_type}.")
				return
		except discord.Forbidden:
			logging.error(f"No permission to modify roles of member {member_name}.")
			return
		except discord.HTTPException as e:
			logging.error(f"Failed to modify roles of member {member_name}: {e}")
			return

	@staticmethod
	def discord_user_to_full_name(user: typing.Union[discord.User, discord.Member, discord.ClientUser]):
		return f"{user.name} ({user.display_name})"
