# Team Steelaxe Discord Bot

This is the bot providing some commands and functions for the [Team Steelaxe Discord Server](https://discord.gg/antielitz).

To run, install requirements:

```
pip install -r requirements.txt
```

Then copy the config template [config.json.template](config.json.template) to `config.json` and fill in the discord bot token.

### Reaction Roles

To add a role that is managed by a reaction to a message, fill in the necessary values into `config.json` and restart the bot.

* emoji: The Unicode Emoji as string or the ID of a custom emoji as int (without double quotes). You can get the custom emoji ID by sending \:emojiname: to any discord channel.
* message-id: The ID of the message that should be reacted to. You can get it by rightclicking on the message -> Copy Message ID. You need to have [developer mode](https://discord.com/developers/docs/game-sdk/store#application-test-mode) enabled.
* role-id: The ID of the role that should be given upon reaction. You can get it under Server Settings -> Roles, then rightclicking on the role -> Copy Role ID. You need to have [developer mode](https://discord.com/developers/docs/game-sdk/store#application-test-mode) enabled.
