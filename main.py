import os
import time
import logging
from gmail_client import GmailClient
from rule_engine import RuleEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

POLL_INTERVAL = 30  # 초


def process_message(client, engine, message):
    try:
        email = client.get_message_details(message['id'])

        # INBOX에 없는 메시지 스킵 (스팸함 등)
        if 'INBOX' not in email.get('label_ids', []):
            return

        matched_rules = engine.match(email)
        if not matched_rules:
            return

        log.info(f"매칭된 메일: [{email['from']}] {email['subject']}")
        for rule in matched_rules:
            actions = rule.get('actions', {})
            label = actions.get('label')
            mark_read = actions.get('mark_read', False)
            client.apply_actions(email['id'], label_name=label, mark_read=mark_read)
            log.info(f"  → 규칙 '{rule['name']}' 적용 완료 (label={label}, mark_read={mark_read})")

    except Exception as e:
        log.error(f"메시지 처리 오류 (id={message['id']}): {e}")


def main():
    # secrets/credentials.json 파일 확인
    if not os.path.exists('secrets/credentials.json'):
        log.error("secrets/credentials.json 파일이 없습니다. README를 참고하여 추가해주세요.")
        return

    log.info("Gmail Organizer 시작")
    client = GmailClient()
    engine = RuleEngine()

    history_id = client.get_current_history_id()
    log.info(f"초기 historyId: {history_id}")
    log.info(f"{POLL_INTERVAL}초 간격으로 새 메일 감지 시작...")

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            engine.reload()  # rules.json 변경사항 자동 반영

            messages, history_id = client.get_new_messages(history_id)
            if messages:
                log.info(f"새 메시지 {len(messages)}개 감지")
                for msg in messages:
                    process_message(client, engine, msg)

        except KeyboardInterrupt:
            log.info("종료합니다.")
            break
        except Exception as e:
            log.error(f"폴링 오류: {e}")


if __name__ == '__main__':
    main()
