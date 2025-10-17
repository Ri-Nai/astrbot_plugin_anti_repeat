# /astrbot_plugin_anti_repeat/main.py

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.core import logger

ß


@register(
    "astrbot_plugin_anti_repeat",
    "Ri-Nai",
    "一个基于 LLM 的历史聊天记录防复读插件，支持打断（或者撤回）复读消息。",
    "1.0.0",
)
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        # 1. 加载配置
        self.config = config
        self.group_list = config.get("group_list", [])
        self.message_limit = config.get("message_limit", 3)
        self.need_recall = config.get("need_recall", False)
        self.last_messages = {}  # 用于存储每个群的最后一条消息

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_listen(self, event: AstrMessageEvent, arg: str = None):
        """监听群消息，防止复读"""
        group_id = event.get_group_id()
        if self.group_list and group_id not in self.group_list:
            return  # 如果配置了群列表且当前群不在列表中，则忽略
        message_text = event.get_message_str()
        if group_id not in self.last_messages:
            self.last_messages[group_id] = []
        self.last_messages[group_id].append(message_text)
        if len(self.last_messages[group_id]) > self.message_limit:
            self.last_messages[group_id].pop(0)
        # 检查是否复读
        if len(self.last_messages[group_id]) == self.message_limit and all(
            msg == message_text for msg in self.last_messages[group_id]
        ):
            yield event.plain_text("检测到复读消息！")

    async def terminate(self):
        """插件卸载时的清理操作"""
        logger.info("防撤回插件已卸载")
