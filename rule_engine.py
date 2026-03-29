import json
import logging

log = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, rules_path='rules.json'):
        self.rules_path = rules_path
        self.rules = self._load_rules()

    def _load_rules(self):
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rules = data.get('rules', [])
        log.info(f"규칙 {len(rules)}개 로드됨")
        return rules

    def reload(self):
        self.rules = self._load_rules()

    def match(self, email):
        """이메일에 매칭되는 규칙 목록 반환"""
        return [rule for rule in self.rules if self._check_rule(rule, email)]

    def _check_rule(self, rule, email):
        conditions = rule.get('conditions', {})
        match_type = rule.get('match', 'any')  # 'any' = OR, 'all' = AND

        results = []

        if 'sender' in conditions:
            sender_lower = email['from'].lower()
            results.append(
                any(s.lower() in sender_lower for s in conditions['sender'])
            )

        if 'keywords' in conditions:
            subject_lower = email['subject'].lower()
            results.append(
                any(kw.lower() in subject_lower for kw in conditions['keywords'])
            )

        if not results:
            return False

        return all(results) if match_type == 'all' else any(results)
