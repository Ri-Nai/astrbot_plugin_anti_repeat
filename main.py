# /astrbot_plugin_anti_repeat/main.py

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.core import logger
from astrbot.api.message_components import (
    Image,
    BaseMessageComponent,
)


def message_to_dict(message: BaseMessageComponent):
    """将消息组件转换为字典形式，便于比较"""
    if isinstance(message, Image):
        return {
            "type": "Image",
            "data": {
                "file": message.file,
            },
        }
    else:
        return message.toDict()

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
        self.roles = {}  # 用于存储每个群的角色信息
        self.user_id = None  # 机器人自己的用户ID

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_listen(self, event: AstrMessageEvent):
        """监听群消息，防止复读"""
        group_id = event.get_group_id()
        client = event.bot
        if self.user_id is None:
            login_info = await client.api.call_action("get_login_info")
            self.user_id = login_info.get("user_id")
        if self.group_list and group_id not in self.group_list:
            return  # 如果配置了群列表且当前群不在列表中，则忽略
        message = event.message_obj
        message_str = event.message_str
        message_content = str(list(map(message_to_dict, message.message)))
        message_id = message.message_id
        if message_content == "[]" or message_content.strip() == "":
            return  # 忽略空消息
        if group_id not in self.last_messages:
            self.last_messages[group_id] = []
        self.last_messages[group_id].append(message_content)
        if len(self.last_messages[group_id]) > self.message_limit:
            self.last_messages[group_id].pop(0)

        if group_id not in self.roles:
            group_info = await client.api.call_action(
                "get_group_member_info",
                group_id=group_id,
                user_id=self.user_id,
            )
            self.roles[group_id] = group_info.get("role", "member")
        can_recall = self.roles[group_id] in ("admin", "owner") and self.need_recall
        # 检查是否复读
        if len(self.last_messages[group_id]) == self.message_limit and all(
            msg == message_content for msg in self.last_messages[group_id]
        ):
            if can_recall:
                try:
                    await client.api.call_action(
                        "delete_msg",
                        message_id=message_id,
                    )
                    self.last_messages[group_id].pop()  # 移除刚撤回的消息，防止重复触发
                    yield event.plain_result(
                        f"检测到复读消息{message_str}，已撤回！"
                    )
                except Exception as e:
                    yield event.plain_result(
                        f"检测到复读消息{message_str}，但撤回失败：{e}"
                    )
            else:
                self.last_messages[group_id] = []  # 清空记录，防止重复触发
                yield event.plain_result(f"检测到复读消息{message_str}！")

    async def terminate(self):
        """插件卸载时的清理操作"""
        logger.info("防撤回插件已卸载")
