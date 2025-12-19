# 实际应用伪代码
class MemorySystem:
    def __init__(self):
        self.memories = []  # 所有记忆

    def extract_anchors(self, text: str) -> List[Anchor]:
        """从文本提取锚点"""
        anchors = []

        # 1. 基于NER模型提取
        ner_anchors = self._extract_by_ner(text)
        anchors.extend(ner_anchors)

        # 2. 规则引擎补充
        rule_anchors = self._extract_by_rules(text)
        anchors.extend(rule_anchors)

        # 3. 置信度调整和去重
        anchors = self._deduplicate_anchors(anchors)

        return anchors

    def add_conversation(self, user_text):
        # 提取锚点
        anchors = extract_anchors(user_text)

        # 存储
        for anchor in anchors:
            self.memories.append(anchor)

            # 建立索引
            self.update_index(anchor)

    def respond(self, user_query):
        # 1. 查找相关记忆
        relevant = self.find_relevant(user_query)

        # 2. 根据记忆生成回复
        if has_constraint(user_query, relevant):
            return "根据您的限制，我建议..."
        else:
            return "根据您的偏好，我推荐..."

    # 提取用户说的限制条件
    def extract_constraints(text):
        if "不能" in text or "避免" in text:
            return {
                "type": "constraint",
                "content": text,
                "confidence": 0.9
            }
        return None